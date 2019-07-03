import datetime
import email.utils
import html
import http.client
import io
import mimetypes
import os
import posixpath
import selectors
import shutil
import socket
import sys
import time
import urllib.parse

from functools import reduce
from http import HTTPStatus
from traceback import format_exc
from typing import Callable, List

# Callback to write formatted log strings.
_log = sys.stderr.write
# Try to read system mimetypes
if not mimetypes.inited:
    mimetypes.init()
EXTENSIONS_MAP = mimetypes.types_map.copy()


def _guess_type(path):
    """ Guess the type of a file. Argument is a PATH (filename). """
    _, ext = posixpath.splitext(path)
    return EXTENSIONS_MAP.get(ext) or EXTENSIONS_MAP.get(ext.lower()) or 'text/html'


class HTTPError(Exception):

    NO_BODY = {HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED}

    def to_html(self) -> bytes:
        code, message = self.args
        text = '<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html"></head><body>' \
               f'<h1>HTTP Error {code}</h1><h3>{html.escape(message, quote=False)}</h3></body></html>'
        return text.encode('utf-8', 'replace')

    def is_bodyless(self) -> bool:
        """ Message body is omitted for 204 (No Content), 205 (Reset Content), 304 (Not Modified). """
        code, _ = self.args
        return code < 200 or code in self.NO_BODY

    def __str__(self) -> str:
        code, message = self.args
        return f"ERROR {code} - {message}"


class _SocketWriter(io.BufferedIOBase):
    """ Simple writable BufferedIOBase implementation for a socket.
        Does not hold data in a buffer, avoiding any need to call flush(). """

    def __init__(self, sock):
        self._sock = sock

    def writable(self) -> bool:
        return True

    def write(self, b:bytes) -> int:
        self._sock.sendall(b)
        return len(b)

    def fileno(self) -> int:
        return self._sock.fileno()


class SpectraRequestHandler:
    """ This class is instantiated for each request to be handled.
        The constructor sets the instance variables request, client_address and then calls the handle() method.
        The handle() method can find the request as self.request, and the client address as self.client_address. """

    # hack to maintain backwards compatibility
    _RESPONSES = {v: (v.phrase, v.description) for v in HTTPStatus.__members__.values()}

    # The default request version. Most web servers default to HTTP 0.9, i.e. don't send a status line.
    DEFAULT_REQUEST_VERSION = "HTTP/0.9"
    PROTOCOL_VERSION = "HTTP/1.1"  # HTTP 1.1 is required for automatic keepalive.
    VERSION_STRING = f"Spectra/0.1 Python/{sys.version.split()[0]}"  # The server software version string.

    request: socket.socket  # Main socket object to read/write to.
    client_address: tuple   # Tuple of (addr, port) for client.
    process_POST: Callable  # Main callback to process user state.
    directory: str          # Root directory for public HTTP files.

    _headers_buffer: List[str]  # List of strings to be joined and encoded as the final header.
    _rfile: io.BufferedIOBase   # File object from which the request is read.
    _wfile: _SocketWriter       # File object to which the reply is written.

    requestline = request_version = command = ''
    close_connection = True

    def __init__(self, request:socket.socket, client_address:tuple, *, callback:Callable, directory:str):
        self.request = request
        self.client_address = client_address
        self.process_POST = callback
        self.directory = directory
        self._headers_buffer = []
        self._rfile = request.makefile('rb')
        self._wfile = _SocketWriter(request)
        try:
            # Handle multiple requests if necessary.
            self.handle_request()
            while not self.close_connection:
                self.handle_request()
        finally:
            self._wfile.close()
            self._rfile.close()

    def handle_request(self, uri_max_len=65536) -> None:
        """ Handle a single HTTP request. """
        try:
            self.raw_requestline = self._rfile.readline(uri_max_len + 1)
            if len(self.raw_requestline) > uri_max_len:
                raise HTTPError(HTTPStatus.REQUEST_URI_TOO_LONG, 'URI is too long')
            if not self.raw_requestline:
                self.close_connection = True
                return
            self.parse_request()
            method = getattr(self, f'do_{self.command}', None)
            if method is None:
                raise HTTPError(HTTPStatus.NOT_IMPLEMENTED, f"Unsupported method ({self.command})")
            method()
        except HTTPError as e:
            # Send the error code, then exit.
            self.send_error(e)
        except socket.timeout as e:
            # a read or a write timed out. Discard this connection.
            self.log_message(f"Request timed out: {e!r}")
            self.close_connection = True

    def parse_request(self) -> None:
        """ Parse a request. The request should be stored in self.raw_requestline;
            the results are in self.command, self.path, self.request_version and self.headers. """
        self.request_version = self.DEFAULT_REQUEST_VERSION
        self.close_connection = True
        self.requestline = requestline = str(self.raw_requestline, 'iso-8859-1').rstrip('\r\n')
        try:
            self.command, self.path, *opt_version = requestline.split()
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad request syntax ({requestline!r})")
        keepalive_supported = (self.PROTOCOL_VERSION >= "HTTP/1.1")
        if opt_version:
            version = opt_version[-1]
            try:
                if not version.startswith('HTTP/'):
                    raise ValueError
                base_version_number = version.split('/', 1)[1]
                # There can be only one "." and major and minor numbers MUST be treated as separate integers.
                major, minor = map(int, base_version_number.split("."))
            except (ValueError, IndexError):
                raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad request version ({version!r})")
            if (major, minor) >= (1, 1) and keepalive_supported:
                self.close_connection = False
            if major >= 2:
                raise HTTPError(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, f"Invalid HTTP version ({base_version_number})")
            self.request_version = version
        elif self.command != 'GET':
            raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad HTTP/0.9 request type ({self.command!r})")
        # Examine the headers and look for a Connection directive.
        self._parse_headers()
        conntype = self.headers.get('Connection', "").lower()
        if conntype == 'close':
            self.close_connection = True
        elif conntype == 'keep-alive' and keepalive_supported:
            self.close_connection = False
        # Examine the headers and look for an Expect directive. Default is to always respond with a 100 Continue.
        expect = self.headers.get('Expect', "").lower()
        if expect == "100-continue" and keepalive_supported and self.request_version >= "HTTP/1.1":
            code = HTTPStatus.CONTINUE
            message, _ = self._RESPONSES.get(code, ('', ''))
            self.add_response_only(code, message)
            self.end_headers()

    def _parse_headers(self, header_max_len=65536, header_max_count=100) -> None:
        """ Parse RFC2822 headers from a file pointer. """
        header_lines = []
        line = None
        while line not in {b'\r\n', b'\n', b''}:
            line = self._rfile.readline(header_max_len + 1)
            if len(line) > header_max_len:
                raise HTTPError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Header line too long.")
            header_lines.append(line)
            if len(header_lines) > header_max_count:
                raise HTTPError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Too many headers.")
        hstring = b''.join(header_lines).decode('iso-8859-1')
        self.headers = email.parser.Parser(_class=http.client.HTTPMessage).parsestr(hstring)

    def send_error(self, err:HTTPError) -> None:
        """ Send and log an error reply, then send a piece of HTML explaining the error to the user. """
        self.log_message(str(err))
        self.add_response(*err.args)
        self.add_header('Connection', 'close')
        self.close_connection = True
        if self.command == 'HEAD' or err.is_bodyless():
            self.end_headers()
        else:
            self._send_data(err.to_html())

    def add_response(self, code:int, message:str=None) -> None:
        """ Add the response header to the headers buffer and log the response code.
            Also add two standard headers with the server software version and the current date. """
        self.log_message(f'"{self.requestline}" {code}')
        if message is None:
            message, _ = self._RESPONSES.get(code) or ('', '')
        self.add_response_only(code, message)
        self.add_header('Server', self.VERSION_STRING)
        self.add_header('Date', self.date_time_string())

    def add_response_only(self, code:int, message:str) -> None:
        """ Add the response header only. """
        self._headers_buffer.append(f"{self.PROTOCOL_VERSION} {code} {message}")

    def add_header(self, keyword, value) -> None:
        """ Add a header to the headers buffer. """
        self._headers_buffer.append(f"{keyword}: {value}")

    def end_headers(self) -> None:
        """ Add the blank line ending the MIME headers and flush (assuming there is at least one line). """
        buf = self._headers_buffer
        if buf and self.request_version != 'HTTP/0.9':
            buf += ("", "")
            header = "\r\n".join(buf)
            self._wfile.write(header.encode('latin-1', 'strict'))
        buf.clear()

    def log_message(self, message:str) -> None:
        """ Log an arbitrary message using the log callback. """
        _log(f'{self.client_address[0]} [{time.strftime("%b %d %Y %H:%M:%S")}] {message}\n')

    def date_time_string(self, timestamp=None):
        """ Return the current date and time formatted for a message header. """
        return email.utils.formatdate(timestamp, usegmt=True)

    def _do_GET_or_HEAD(self) -> None:
        """ Common code for GET and HEAD commands. This sends the response code and MIME headers. """
        file_path = self._translate_path()
        try:
            f = open(file_path, 'rb')
        except OSError:
            raise HTTPError(HTTPStatus.NOT_FOUND, f'File "{self.path}" not found')
        with f:
            fs = os.fstat(f.fileno())
            mtime = fs.st_mtime
            if not self._modified_since(mtime):
                self.add_response(HTTPStatus.NOT_MODIFIED)
                self.end_headers()
                return
            ctype = _guess_type(file_path)
            self.add_response(HTTPStatus.OK)
            self.add_header("Content-type", ctype)
            self.add_header("Content-Length", str(fs[6]))
            self.add_header("Last-Modified", self.date_time_string(mtime))
            self.end_headers()
            # A file is copied to the output unless the command was HEAD.
            if self.command != 'HEAD':
                shutil.copyfileobj(f, self._wfile)

    do_GET = _do_GET_or_HEAD
    do_HEAD = _do_GET_or_HEAD

    def _translate_path(self) -> str:
        """ Translate self.path to the local filename syntax. Tokens special to the local file system are ignored. """
        # Remove query parameters.
        path = self.path.split('?', 1)[0].split('#', 1)[0]
        # Don't forget explicit trailing slash when normalizing.
        trailing_slash = path.rstrip().endswith('/')
        try:
            path = urllib.parse.unquote(path, errors='surrogatepass')
        except UnicodeDecodeError:
            path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        # Ignore components that are not a simple file/directory name.
        words = [word for word in path.split('/') if word and word[0] != '.' and not os.path.dirname(word)]
        path = reduce(os.path.join, words, self.directory)
        if trailing_slash:
            path += '/'
        # Route bare directory paths to index.html (whether or not it exists).
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        return path

    def _modified_since(self, mtime:int, tz=datetime.timezone.utc) -> bool:
        """ Use browser cache if possible. Compare If-Modified-Since and time of last file modification. """
        header_mtime = self.headers.get("If-Modified-Since")
        if header_mtime is not None and "If-None-Match" not in self.headers:
            try:
                ims = email.utils.parsedate_to_datetime(header_mtime)
            except (TypeError, IndexError, OverflowError, ValueError):
                return True
            if ims.tzinfo is None:
                # obsolete format with no timezone, cf.
                ims = ims.replace(tzinfo=tz)
            if ims.tzinfo is tz:
                # compare to UTC datetime of last modification.
                last_modif = datetime.datetime.fromtimestamp(mtime, tz)
                # remove microseconds, like in If-Modified-Since.
                last_modif = last_modif.replace(microsecond=0)
                return last_modif > ims
        return True

    def do_POST(self) -> None:
        """ Start service of a POST request. """
        data = self._receive_data()
        self.process_POST(data, self.finish_POST)

    def finish_POST(self, response:bytes) -> None:
        """ Finish the request by sending the processed data. """
        self.add_response(HTTPStatus.OK)
        self._send_data(response, "application/json")

    def _receive_data(self) -> bytes:
        """ Return any request content data as a bytes object. """
        size = int(self.headers["Content-Length"])
        data = self._rfile.read(size)
        return data

    def _send_data(self, response:bytes, ctype:str="text/html") -> None:
        """ Write the response headers and data for content with MIME type <ctype>. """
        self.add_header("Content-Type", ctype)
        self.add_header("Content-Length", str(len(response)))
        self.end_headers()
        self._wfile.write(response)


class SpectraHTTPServer:
    """ Class for socket-based synchronous TCP/IP stream server. """

    REQUEST_QUEUE_SIZE = 5
    HANDLER_CLS = SpectraRequestHandler

    _handler_kwargs: dict   # Keyword args to add to every request.
    _socket: socket.socket  # Master TCP socket.

    do_shutdown: bool = False   # Set to True to stop the serve_forever loop.

    def __init__(self, server_address, **kwargs):
        self._handler_kwargs = kwargs
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Bind the socket and activate the server.
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(server_address)
            self._server_address = self._socket.getsockname()
            self._socket.listen(self.REQUEST_QUEUE_SIZE)
        except:
            self._socket.close()
            raise

    def serve_forever(self, poll_interval:float=0.5) -> None:
        """ Handle one request at a time until shutdown. Polls for shutdown every poll_interval seconds. """
        with selectors.SelectSelector() as selector:
            selector.register(self._socket, selectors.EVENT_READ)
            while not self.do_shutdown:
                ready = selector.select(poll_interval)
                if ready:
                    self._handle_request()

    def _handle_request(self) -> None:
        """ Handle one request by instantiating handler_cls with the kwargs given at __init__. """
        try:
            request, client_address = self._socket.accept()
        except OSError:
            return
        try:
            self.HANDLER_CLS(request, client_address, **self._handler_kwargs)
        except Exception:
            hr = ('-' * 40) + '\n'
            _log(f'{hr}Exception during processing of request from {client_address}\n{format_exc()}{hr}')
        finally:
            # socket.close() releases the socket and waits for GC to perform the actual close.
            # some platforms may raise ENOTCONN here.
            try:
                request.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            request.close()

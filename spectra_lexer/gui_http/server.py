import datetime
import email.utils
import html
import io
import os
import posixpath
import selectors
import socket
import sys
import time
import urllib.parse

from http import HTTPStatus
from mimetypes import MimeTypes
from threading import Thread
from traceback import format_exc
from typing import Callable, List

from .base import GUIHTTP


class HTTPError(Exception):

    NO_BODY = {HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED}

    def to_html(self) -> bytes:
        """ There should be at least one arg: the HTTP code. Others are added as custom messages. """
        code, *messages = self.args
        lines = ['<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html"></head><body>',
                 f'<h1>HTTP Error {code}</h1>',
                 *[f'<h3>{html.escape(m, quote=False)}</h3>' for m in messages],
                 '</body></html>']
        return "".join(lines).encode('utf-8', 'replace')

    def is_bodyless(self) -> bool:
        """ Message body is omitted for 204 (No Content), 205 (Reset Content), 304 (Not Modified). """
        code = self.args[0]
        return code < 200 or code in self.NO_BODY

    def __str__(self) -> str:
        code, *messages = self.args
        return " - ".join([f'ERROR {code:d}', *messages])


class SpectraRequestHandler:
    """ HTTP request handler class, instantiated once for each connection, followed by a single __call__.
        Usually handles only one request per instantiation, but sometimes more with keep-alive enabled.
        If this is the case, threading is required so that one client can't hog the entire server. """

    _GET_MIMETYPE = MimeTypes().guess_type
    _LOG = sys.stderr.write  # Callback to write formatted log strings.

    # The default request version. Most web servers default to HTTP 0.9, i.e. don't send a status line.
    DEFAULT_REQUEST_VERSION = "HTTP/0.9"
    PROTOCOL_VERSION = "HTTP/1.1"  # HTTP 1.1 is required for automatic keepalive.
    VERSION_STRING = f"Spectra/0.1 Python/{sys.version.split()[0]}"  # The server software version string.

    request: socket.socket  # Main socket object to which the reply is written.
    address: str            # Client IP address.
    port: int               # Client TCP port.
    process_POST: Callable  # Main callback to process user state.
    directory: str          # Root directory for public HTTP files.

    _headers_buffer: List[str]  # List of strings to be joined and encoded as the final header.
    _rfile: io.BufferedReader   # Buffered file object from which the request is read.

    requestline = request_version = command = path = ''
    close_connection = True

    def __init__(self, request:socket.socket, address:str, port:int, *, callback:Callable, directory:str):
        self.request = request
        self.address = address
        self.port = port
        self.process_POST = callback
        self.directory = directory
        self._headers_buffer = []
        self._rfile = request.makefile('rb')

    def __call__(self) -> None:
        """ Handle one or more HTTP requests. """
        try:
            self.log_message("Connection opened.")
            self._handle_request()
            while not self.close_connection:
                self._handle_request()
        except HTTPError as e:
            self.log_message(str(e))
            self.send_error(e)
        except socket.timeout as e:
            self.log_message(f"Request timed out: {e!r}")
        except OSError:
            self.log_message("Connection aborted by OS.")
        except Exception:
            self.log_message(format_exc())
        finally:
            try:
                self.request.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            self._rfile.close()
            self.request.close()
            self.log_message("Connection terminated.")

    def _handle_request(self) -> None:
        """ Handle a single HTTP request. """
        self.raw_requestline = self._readline_header()
        if not self.raw_requestline:
            self.close_connection = True
            return
        self.parse_request()
        method = getattr(self, f'do_{self.command}', None)
        if method is None:
            raise HTTPError(HTTPStatus.NOT_IMPLEMENTED, f"Unsupported method: ({self.command})")
        method()

    def parse_request(self) -> None:
        """ Parse a request. The request should be stored in self.raw_requestline;
            the results are in self.command, self.path, self.request_version and self.headers. """
        self.request_version = self.DEFAULT_REQUEST_VERSION
        self.close_connection = True
        self.requestline = requestline = str(self.raw_requestline, 'iso-8859-1').rstrip('\r\n')
        try:
            self.command, self.path, *opt_version = requestline.split()
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad request syntax: ({requestline!r})")
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
                raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad request version: ({version!r})")
            if (major, minor) >= (1, 1) and keepalive_supported:
                self.close_connection = False
            if major >= 2:
                raise HTTPError(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, f"Invalid HTTP version: ({base_version_number})")
            self.request_version = version
        elif self.command != 'GET':
            raise HTTPError(HTTPStatus.BAD_REQUEST, f"Bad HTTP/0.9 request type: ({self.command!r})")
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
            self.add_response_only(HTTPStatus.CONTINUE)
            self.end_headers()

    def _parse_headers(self, header_max_count:int=100) -> None:
        """ Parse RFC2822 headers from a file pointer. """
        header_lines = []
        line = None
        while line not in {b'\r\n', b'\n', b''}:
            line = self._readline_header()
            header_lines.append(line)
            if len(header_lines) > header_max_count:
                raise HTTPError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Too many headers.")
        hstring = b''.join(header_lines).decode('iso-8859-1')
        self.headers = email.parser.Parser().parsestr(hstring)

    def send_error(self, err:HTTPError) -> None:
        """ Send an error reply, then send a piece of HTML explaining the error to the user. """
        self.add_response(*err.args)
        self.add_header('Connection', 'close')
        if self.command == 'HEAD' or err.is_bodyless():
            self.end_headers()
        else:
            self._send_data(err.to_html())

    def add_response(self, code:HTTPStatus, *args) -> None:
        """ Add the response header to the headers buffer and log the response code.
            Also add two standard headers with the server software version and the current date. """
        self.log_message(f'"{self.requestline}" {code}')
        self.add_response_only(code, *args)
        self.add_header('Server', self.VERSION_STRING)
        self.add_header('Date', self.date_time_string())

    def add_response_only(self, code:HTTPStatus, message:str=None) -> None:
        """ Add the response header only. """
        self._headers_buffer.append(f"{self.PROTOCOL_VERSION} {code} {message or code.phrase}")

    def add_header(self, keyword:str, value:str) -> None:
        """ Add a header to the headers buffer. """
        self._headers_buffer.append(f"{keyword}: {value}")

    def end_headers(self) -> None:
        """ Add the blank line ending the MIME headers and flush (assuming there is at least one line). """
        buf = self._headers_buffer
        if buf and self.request_version != 'HTTP/0.9':
            buf += ("", "")
            header = "\r\n".join(buf)
            self._write(header.encode('latin-1', 'strict'))
        buf.clear()

    def log_message(self, message:str) -> None:
        """ Log an arbitrary message using the log callback. """
        self._LOG(f'{self.address} [{time.strftime("%b %d %Y %H:%M:%S")}] {message}\n')

    @staticmethod
    def date_time_string(timestamp:float=None) -> str:
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
            ctype, _ = self._GET_MIMETYPE(file_path)
            self.add_response(HTTPStatus.OK)
            self._send_data(f.read(), ctype, mtime)

    do_GET = _do_GET_or_HEAD
    do_HEAD = _do_GET_or_HEAD

    def _translate_path(self) -> str:
        """ Translate self.path to the local filename syntax. Tokens special to the local file system are ignored. """
        # Remove query parameters.
        path = self.path.split('?', 1)[0].split('#', 1)[0]
        # Don't forget explicit trailing slash when normalizing.
        trailing_slash = path.rstrip().endswith('/')
        path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)
        # Ignore components that are not a simple file/directory name.
        words = [word for word in path.split('/') if word and word[0] != '.' and not os.path.dirname(word)]
        path = os.path.join(self.directory, *words)
        # Route bare directory paths to index.html (whether or not it exists).
        if os.path.isdir(path) or trailing_slash:
            path = os.path.join(path, "index.html")
        return path

    def _modified_since(self, mtime:float, tz=datetime.timezone.utc) -> bool:
        """ Use browser cache if possible. Compare If-Modified-Since and time of last file modification. """
        header_mtime = self.headers.get("If-Modified-Since")
        if header_mtime is not None and "If-None-Match" not in self.headers:
            try:
                ims = email.utils.parsedate_to_datetime(header_mtime)
            except (TypeError, IndexError, OverflowError, ValueError):
                return True
            if ims.tzinfo is None:
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
        return self._read(size)

    def _send_data(self, response:bytes, ctype:str="text/html", mtime:float=None) -> None:
        """ Write the response headers and data for content with MIME type <ctype>. """
        self.add_header("Content-Type", ctype)
        self.add_header("Content-Length", str(len(response)))
        if mtime is not None:
            self.add_header("Last-Modified", self.date_time_string(mtime))
        self.end_headers()
        # Only send the content if the command was not HEAD.
        if self.command != 'HEAD':
            self._write(response)

    def _read(self, size:int) -> bytes:
        return self._rfile.read(size)

    def _readline_header(self, max_len:int=65536) -> bytes:
        line = self._rfile.readline(max_len + 1)
        if len(line) > max_len:
            raise HTTPError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE, "Header line too long.")
        return line

    def _write(self, data:bytes) -> int:
        self.request.sendall(data)
        return len(data)


class ThreadedRequestHandler(SpectraRequestHandler):

    def __call__(self) -> None:
        """ Handle each request with a new thread. """
        Thread(target=super().__call__, daemon=True).start()


class HttpServer(GUIHTTP):
    """ Class for socket-based synchronous TCP/IP stream server. """

    _REQUEST_QUEUE_SIZE = 10  # Maximum allowed requests in the queue before dropping any.
    _POLL_INTERVAL = 0.5      # Poll for shutdown every <POLL_INTERVAL> seconds.

    shutdown: bool = False    # Set to True to stop the server loop.

    def GUIHTTPServe(self) -> None:
        """ Bind a TCP/IP socket, activate the server, and listen for one request at a time until shutdown. """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(self.ADDRESS)
            sock.listen(self._REQUEST_QUEUE_SIZE)
            self._serve(sock)

    def _serve(self, sock:socket.socket) -> None:
        with selectors.SelectSelector() as selector:
            selector.register(sock, selectors.EVENT_READ)
            while not self.shutdown:
                if selector.select(self._POLL_INTERVAL):
                    self._accept(sock)

    def _accept(self, sock:socket.socket) -> None:
        """ Handle each request by instantiating the handler with the required kwargs and calling it. """
        try:
            request, addr = sock.accept()
        except OSError:
            return
        ThreadedRequestHandler(request, *addr, callback=self.GUIHTTPRequest, directory=self.HTTP_PUBLIC)()

    def GUIHTTPShutdown(self) -> None:
        self.shutdown = True

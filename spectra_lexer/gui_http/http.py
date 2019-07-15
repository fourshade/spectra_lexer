import datetime
import email.utils
import os
import socket
import sys
from http import HTTPStatus
from mimetypes import MimeTypes
from traceback import format_exc
from typing import Callable, List


class HTTPError(Exception):

    NO_BODY = {*range(100, 200), HTTPStatus.NO_CONTENT, HTTPStatus.RESET_CONTENT, HTTPStatus.NOT_MODIFIED}
    HTML_SUB = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})

    html: bytes = None  # Encoded HTML document to send to the user.

    def __init__(self, code:HTTPStatus=HTTPStatus.INTERNAL_SERVER_ERROR, *messages:str):
        """ The first arg must be the HTTP code (default 500). Other args are added as custom messages.
            The message body is omitted for 1xx, 204 (No Content), 205 (Reset Content), 304 (Not Modified). """
        self.args = code, *messages
        if code not in self.NO_BODY:
            self.html = ('<!DOCTYPE html><html><head><meta http-equiv="Content-Type" content="text/html"></head><body>'
                         f'<h1>HTTP Error {code} - {code.phrase}</h1>'
                         f'<h3>{": ".join([code.description, *messages]).translate(self.HTML_SUB)}</h3>'
                         '</body></html>').encode('utf-8', 'replace')


class HttpRequestURI:

    _HEX_SUB = {bytes([b]).hex(): chr(b) for b in range(128)}

    path: str = ''
    query: dict
    fragment: str = ''

    def __init__(self, uri:str):
        """ Parse the URI into components. """
        if '#' in uri:
            uri, fragment = uri.split('#', 1)
            self.fragment = self._unquote_plus(fragment)
        self.query = {}
        if '?' in uri:
            uri, query = uri.split('?', 1)
            pairs = [s2.split('=', 1)for s1 in query.split('&') for s2 in s1.split(';') if '=' in s2]
            self.query = dict([map(self._unquote_plus, p) for p in pairs])
        self.path = self._unquote_plus(uri)

    def _unquote_plus(self, string:str) -> str:
        """ Replace + and %xx escapes by their single-character equivalent. """
        if '+' in string:
            string = string.replace('+', ' ')
        if '%' not in string:
            return string
        first, *bits = string.split('%')
        res = [first]
        for item in bits:
            try:
                res += self._HEX_SUB[item[:2].lower()], item[2:]
            except KeyError:
                res += '%', item
        return ''.join(res)


class HttpRequestHeaders:

    raw: list  # Contains the raw string form of every header, even those with duplicate names.
    _d: dict   # Contains the last header with each unique lowercased name.

    def __init__(self, header_lines:list):
        # Create a new message and start by parsing headers.
        self.raw = raw = []
        self._d = d = {}
        for line in header_lines:
            # Search for a line with no colon (including an empty line).
            if ':' not in line:
                # Check for continuation, otherwise quit. A first line continuation is illegal.
                if line and line[0] in ' \t' and raw:
                    raw[-1].append(line)
                    continue
                break
            # Split the line on the colon separating field name from value. There will always be a colon at this point.
            raw.append(line.split(':', 1))
        for source in raw:
            # The name is parsed as everything up to the ':' and returned unmodified.
            # The value is determined by stripping leading whitespace and trailing newline characters.
            name, *values = source
            value = ''.join(values).lstrip().rstrip('\r\n')
            source[:] = name, value
            d[name.lower()] = value

    def get(self, name:str, *args) -> str:
        return self._d.get(name.lower(), *args)


class HttpRequest:

    method: str = ''
    path: str = ''
    query: dict = {}
    content: bytes = b""

    _headers = {}

    def __init__(self, rfile) -> None:
        """ Parse HTTP request data from a socket object. Return True if the connection should be kept alive. """
        request_line, *header_lines = [*self._readline_headers(rfile), ""]
        if not request_line:
            return
        self._parse_requestline(request_line)
        self._headers = HttpRequestHeaders(header_lines)
        len_str = self._headers.get("Content-Length", "")
        if len_str:
            self.content = rfile.read(int(len_str))

    def _readline_headers(self, rfile, size_left:int=65536) -> str:
        """ Read and decode each header line as a string. """
        while True:
            line = rfile.readline(size_left + 1).decode('iso-8859-1').strip()
            size_left -= len(line)
            if size_left < 0:
                raise HTTPError(HTTPStatus.REQUEST_HEADER_FIELDS_TOO_LARGE)
            if not line:
                break
            yield line

    def _parse_requestline(self, request_line:str) -> None:
        """ Parse the request line into a method, URI components, and HTTP request version.  """
        try:
            self.method, uri, version = request_line.split()
            if not version.startswith('HTTP/'):
                raise ValueError
            major, minor = map(int, version[5:].split("."))
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, request_line)
        if major != 1 or minor < 1:
            raise HTTPError(HTTPStatus.HTTP_VERSION_NOT_SUPPORTED, version)
        uri = HttpRequestURI(uri)
        self.path = uri.path
        self.query = uri.query

    def expect_continue(self) -> bool:
        """ Return True if the client is expecting a 100 Continue before it sends any more data. """
        return self._headers.get('Expect', "").lower() == "100-continue"

    def keep_alive(self) -> bool:
        """ Return True if the connection should be kept alive after this request. """
        return self._headers.get('Connection', "").lower() != 'close'

    def modified_since(self, mtime:float) -> bool:
        """ Return True if the given file modification timestamp is later than If-Modified-Since in the header. """
        header_mtime = self._headers.get("If-Modified-Since")
        none_match = self._headers.get("If-None-Match")
        if header_mtime is None or none_match is not None:
            return True
        try:
            ims = email.utils.parsedate_to_datetime(header_mtime)
            last_modif = datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc)
            last_modif = last_modif.replace(microsecond=0)
            return last_modif > ims
        except (TypeError, IndexError, OverflowError, ValueError):
            return True

    def __str__(self) -> str:
        """ Return a summary of the request for a log. """
        return f'{self.method} {self.path}'


class BaseHttpConnection:
    """ HTTP request handler class, instantiated once for each connection, followed by a single __call__.
        Threading is required so that one client can't hog the entire server with keep-alive. """

    _GET_MIMETYPE = MimeTypes().guess_type

    PROTOCOL_VERSION = "HTTP/1.1"  # HTTP >= 1.1 is required for automatic keepalive.
    VERSION_STRING = f"Spectra/0.1 Python/{sys.version.split()[0]}"  # Server software version string.

    log: Callable   # Callback to write formatted log strings.
    directory: str  # Root directory for public HTTP files.

    _rsocket: socket.socket    # Main socket object to which the reply is written.

    request: HttpRequest = None
    response_headers: List[str]  # List of strings to be joined and encoded as the final header.

    def __init__(self, rsocket:socket.socket, directory:str=None, logger:Callable=sys.stderr.write):
        self._rsocket = rsocket
        self.log = logger
        self.directory = directory
        self.response_headers = []

    def __call__(self) -> None:
        """ Process an HTTP connection and requests. """
        try:
            self.log("Connection opened.")
            try:
                self.handle_requests()
            except HTTPError as e:
                self.handle_error(e)
        except socket.timeout as e:
            self.log(f"Request timed out: {e!r}")
        except OSError:
            self.log("Connection aborted by OS.")
        except Exception:
            self.log(format_exc())
        finally:
            try:
                self._rsocket.shutdown(socket.SHUT_WR)
            except OSError:
                pass
            self._rsocket.close()
            self.log("Connection terminated.")

    def handle_requests(self) -> None:
        """ Handle one or more HTTP requests. """
        with self._rsocket.makefile('rb') as rfile:  # Buffered file object from which the request is read.
            while True:
                self.request = request = HttpRequest(rfile)
                method_attr = request.method
                if not method_attr:
                    return
                # Examine the headers and look for continue directives, then call the method.
                if request.expect_continue():
                    self.add_response(HTTPStatus.CONTINUE)
                    self.end_headers()
                func = getattr(self, f'do_{method_attr}', None)
                if func is None:
                    raise HTTPError(HTTPStatus.NOT_IMPLEMENTED, method_attr)
                func()
                if not request.keep_alive():
                    return

    def handle_error(self, err:HTTPError) -> None:
        """ Send an error response and an HTML document explaining the error to the user. """
        self.add_response(err.args[0])
        self.add_header('Connection', 'close')
        body = err.html
        if body is None:
            self.end_headers()
        else:
            self._send_data(body)

    def add_status(self, code:HTTPStatus):
        self.response_headers.append(f"{self.PROTOCOL_VERSION} {code} {code.phrase}")

    def add_header(self, keyword:str, value:str) -> None:
        """ Add a header to the response headers buffer. """
        self.response_headers.append(f"{keyword}: {value}")

    def add_response(self, code:HTTPStatus) -> None:
        """ Add the response header to the headers buffer and log the response code.
            Also add standard headers with the server software version and the current date. """
        self.log(f'"{self.request}" {code}')
        self.add_status(code)
        self.add_header('Server', self.VERSION_STRING)
        self.add_header('Date', self.date_time_string())

    def end_headers(self) -> None:
        """ Add the blank line ending the MIME headers and flush. """
        header = "\r\n".join([*self.response_headers, "", ""])
        self._write(header.encode('latin-1', 'strict'))
        self.response_headers.clear()

    def _send_data(self, response:bytes, ctype:str="text/html") -> None:
        """ Write the entity headers and body for content with MIME type <ctype>. """
        self.add_header("Content-Type", ctype)
        self.add_header("Content-Length", str(len(response)))
        self.end_headers()
        # Only send the content if the command was not HEAD.
        if self.request.method != 'HEAD':
            self._write(response)

    def _write(self, data:bytes) -> int:
        self._rsocket.sendall(data)
        return len(data)

    @staticmethod
    def date_time_string(timestamp:float=None) -> str:
        """ Return the current date and time formatted for a message header. """
        return email.utils.formatdate(timestamp, usegmt=True)

    def _do_GET_or_HEAD(self) -> None:
        """ Common code for GET and HEAD commands. This sends the response code and MIME headers. """
        uri_path = self.request.path
        file_path = self._translate_path(uri_path)
        try:
            f = open(file_path, 'rb')
        except OSError:
            raise HTTPError(HTTPStatus.NOT_FOUND, uri_path)
        with f:
            fs = os.fstat(f.fileno())
            mtime = fs.st_mtime
            if not self.request.modified_since(mtime):
                self.add_response(HTTPStatus.NOT_MODIFIED)
                self.end_headers()
                return
            ctype, _ = self._GET_MIMETYPE(file_path)
            self.add_response(HTTPStatus.OK)
            self.add_header("Last-Modified", self.date_time_string(mtime))
            self._send_data(f.read(), ctype)

    do_GET = _do_GET_or_HEAD
    do_HEAD = _do_GET_or_HEAD

    def _translate_path(self, uri_path:str) -> str:
        """ Translate <uri_path> to the local filename syntax.
            Ignore path components that are not files/directory names, or which point above the root folder. """
        new_comps = []
        for comp in uri_path.strip().split('/'):
            if comp and comp != '.' and not os.path.dirname(comp):
                if comp == '..':
                    if new_comps:
                        new_comps.pop()
                else:
                    new_comps.append(comp)
        file_path = os.path.join(self.directory or os.getcwd(), *new_comps)
        # Route bare directory paths to index.html (whether or not it exists).
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")
        return file_path


class SpectraHttpConnection(BaseHttpConnection):
    """ Handler class specific to client JSON POST requests. """

    process_action: Callable  # Main callback to process user state.

    def __init__(self, *args, process_action:Callable, **kwargs):
        super().__init__(*args, **kwargs)
        self.process_action = process_action

    def do_POST(self) -> None:
        """ Start service of a POST request with JSON data and query parameters. """
        self.process_action(self.request.content, self.send_JSON, **self.request.query)

    def send_JSON(self, response:bytes) -> None:
        """ Finish a request by sending the processed JSON data. """
        self.add_response(HTTPStatus.OK)
        self._send_data(response, "application/json")

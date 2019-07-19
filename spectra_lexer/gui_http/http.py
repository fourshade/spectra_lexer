""" Module for servicing HTTP connections and requests using I/O streams. """

import datetime
import email.utils
from functools import partial
from http import HTTPStatus
from io import RawIOBase
import sys
from traceback import format_exc
from typing import Callable, List


class HTTPErrorMeta(type):

    def __getattr__(cls, name:str) -> Callable:
        """ Create an error exception corresponding directly to a member of HTTPStatus. """
        code = getattr(HTTPStatus, name)
        return partial(cls, code)


class HTTPError(Exception, metaclass=HTTPErrorMeta):

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


class HTTPRequestURI:

    _HEX_SUB = {bytes([b]).hex(): chr(b) for b in range(128)}

    path: str = ''
    query: dict
    fragment: str = ''

    def __init__(self, uri:str):
        """ Parse the URI into components. """
        unquote = self._unquote_plus
        if '#' in uri:
            uri, fragment = uri.split('#', 1)
            self.fragment = unquote(fragment)
        self.query = {}
        if '?' in uri:
            uri, query = uri.split('?', 1)
            pairs = [s2.split('=', 1) for s1 in query.split('&') for s2 in s1.split(';') if '=' in s2]
            self.query = {unquote(k): unquote(v) for k, v in pairs}
        self.path = unquote(uri)

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


class HTTPRequestHeaders:

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


class HTTPRequest:

    method: str = ''
    path: str = ''
    query: dict = {}
    content: bytes = b""

    _headers = {}

    def __init__(self, stream:RawIOBase, max_version:str="HTTP/1.1"):
        """ Parse HTTP request data from a stream object. Return True if the connection should be kept alive. """
        request_line, *header_lines = [*self._readline_headers(stream), ""]
        if not request_line:
            return
        self._parse_requestline(request_line, max_version)
        self._headers = HTTPRequestHeaders(header_lines)
        len_str = self._headers.get("Content-Length")
        if len_str is not None:
            self.content = stream.read(int(len_str))

    def _readline_headers(self, stream:RawIOBase, size_left:int=65536) -> str:
        """ Read and decode each header line as a string. """
        for line in stream:
            size_left -= len(line)
            if size_left < 0:
                raise HTTPError.REQUEST_HEADER_FIELDS_TOO_LARGE()
            line = line.decode('iso-8859-1').strip()
            if not line:
                break
            yield line

    def _parse_requestline(self, request_line:str, max_version:str) -> None:
        """ Parse the request line into a method, URI components, and HTTP request version.  """
        try:
            self.method, uri, version = request_line.split()
            if not version.startswith('HTTP/') or not float(version[5:]):
                raise ValueError
        except ValueError:
            raise HTTPError.BAD_REQUEST(request_line)
        if version > max_version:
            raise HTTPError.HTTP_VERSION_NOT_SUPPORTED(version)
        uri = HTTPRequestURI(uri)
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


class HTTPResponse:

    stream: RawIOBase     # Writable stream for the reply.
    version: str          # HTTP protocol version.
    headers: List[str]    # List of strings to be joined and encoded as the final header.
    content: bytes = b""  # Entity content (blank if none).
    code: HTTPStatus = HTTPStatus.OK

    def __init__(self, stream:RawIOBase, version:str="HTTP/1.1"):
        self.stream = stream
        self.version = version
        self.headers = []

    def add_header(self, keyword:str, value:str) -> None:
        """ Add a header to the response headers buffer. """
        self.headers.append(f"{keyword}: {value}")

    def add_server_info(self, server_version:str) -> None:
        """ Add standard headers with the server software version and the current date. """
        self.add_header('Server', server_version)
        self.add_time('Date')

    def add_time(self, keyword:str, timestamp:float=None) -> None:
        """ Add a header with a formatted date and time from a timestamp (or the current time if None). """
        dt = email.utils.formatdate(timestamp, usegmt=True)
        self.add_header(keyword, dt)

    def add_content(self, content:bytes, ctype:str="text/html") -> None:
        """ Add the entity headers and body for <content> with MIME type <ctype>. """
        self.add_header("Content-Type", ctype)
        self.add_header("Content-Length", str(len(content)))
        self.content = content

    def send(self, code=HTTPStatus.OK) -> None:
        """ Add the status line header and the blank line ending and write everything. """
        self.code = code
        header = "\r\n".join([str(self), *self.headers, "", ""])
        self.stream.write(header.encode('latin-1', 'strict'))
        if self.content:
            self.stream.write(self.content)

    def __str__(self) -> str:
        """ Return the status line as the string value of the response. """
        return f'{self.version} {self.code} {self.code.phrase}'


class HTTPConnectionLogger:
    """ Logger wrapper with a buffer of chained messages which are joined and logged on a direct call. """

    log: Callable[[str], None]
    header: str
    buffer: list

    def __init__(self, logger:Callable[[str], None], header:str):
        self.log = logger
        self.header = header
        self.buffer = []

    def add(self, *messages) -> None:
        self.buffer += messages

    def __call__(self, *messages) -> None:
        """ Add the buffer to the messages, concatenate everything, log it, and start over. """
        self.add(*messages)
        full_message = " -> ".join(map(str, self.buffer))
        self.log(f'{self.header} - {full_message}')
        self.buffer = []


class HTTPConnection:
    """ HTTP request handler class, instantiated once for each connection, followed by a single __call__.
        Threading is required so that one client can't hog the entire server with a persistent connection. """

    PROTOCOL_VERSION = "HTTP/1.1"  # HTTP >= 1.1 is required for automatic keepalive.
    VERSION_STRING = f"Spectra/0.1 Python/{sys.version.split()[0]}"  # Server software version string.

    stream: RawIOBase          # Stream for reading the request and writing the response.
    dispatch: Callable         # Callback for HTTP request processing.
    log: HTTPConnectionLogger  # Callback for writing formatted log strings.

    def __init__(self, stream:RawIOBase, addr:str, dispatcher:Callable, logger:Callable=sys.stderr.write):
        """ Add the client address as a header to each logged message. """
        self.stream = stream
        self.dispatch = dispatcher
        self.log = HTTPConnectionLogger(logger, addr)

    def __call__(self) -> None:
        """ Process an HTTP connection and requests. """
        try:
            self.log("Connection opened.")
            try:
                self.handle_requests()
            except HTTPError as e:
                self.handle_error(e)
        except OSError:
            self.log("Connection aborted by OS.")
        except Exception:
            self.log(format_exc())
        finally:
            self.stream.close()
            self.log("Connection terminated.")

    def handle_requests(self) -> None:
        """ Handle one or more HTTP requests. """
        while True:
            request = HTTPRequest(self.stream, self.PROTOCOL_VERSION)
            if not request.method:
                return
            self.log.add(request)
            # Examine the headers and look for continue directives, then call the method.
            if request.expect_continue():
                self.handle_continue()
            response = self._new_response()
            self.dispatch(request, response)
            self.log(response)
            if not request.keep_alive():
                return

    def handle_continue(self) -> None:
        """ Send a continue response. This cannot have a message body. """
        response = self._new_response()
        response.send(HTTPStatus.CONTINUE)
        self.log(response)

    def handle_error(self, err:HTTPError) -> None:
        """ Send an error response and an HTML document explaining the error to the user. """
        response = self._new_response()
        response.add_header('Connection', 'close')
        body = err.html
        if body is not None:
            response.add_content(body)
        response.send(err.args[0])
        self.log(response)

    def _new_response(self) -> HTTPResponse:
        response = HTTPResponse(self.stream, self.PROTOCOL_VERSION)
        response.add_server_info(self.VERSION_STRING)
        return response

""" Module for servicing HTTP connections and requests using I/O streams. """

import datetime
import email.utils
from functools import partial
from http import HTTPStatus
from io import RawIOBase
from mimetypes import MimeTypes
import os
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

    def __init__(self, stream:RawIOBase):
        """ Parse HTTP request data from a stream object. Return True if the connection should be kept alive. """
        request_line, *header_lines = [*self._readline_headers(stream), ""]
        if not request_line:
            return
        self._parse_requestline(request_line)
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

    def _parse_requestline(self, request_line:str) -> None:
        """ Parse the request line into a method, URI components, and HTTP request version.  """
        try:
            self.method, uri, version = request_line.split()
            if not version.startswith('HTTP/'):
                raise ValueError
            major, minor = map(int, version[5:].split("."))
        except ValueError:
            raise HTTPError.BAD_REQUEST(request_line)
        if major != 1 or minor < 1:
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

    PROTOCOL_VERSION = "HTTP/1.1"  # HTTP >= 1.1 is required for automatic keepalive.
    VERSION_STRING = f"Spectra/0.1 Python/{sys.version.split()[0]}"  # Server software version string.

    stream: RawIOBase  # Writable stream for the reply.
    headers: List[str]  # List of strings to be joined and encoded as the final header.
    content: bytes = b""
    code: HTTPStatus = HTTPStatus.OK

    def __init__(self, stream:RawIOBase, **kwargs):
        """ Add standard headers with the server software version and the current date. """
        self.stream = stream
        self.headers = []
        self.add_header('Server', self.VERSION_STRING)
        self.add_time('Date')

    def __call__(self, *args) -> None:
        """ By default, just send the standard headers and status code. """
        self.send()

    def add_header(self, keyword:str, value:str) -> None:
        """ Add a header to the response headers buffer. """
        self.headers.append(f"{keyword}: {value}")

    def add_time(self, keyword:str, timestamp:float=None) -> None:
        """ Add a header with a formatted date and time from a timestamp (or the current time if None). """
        dt = email.utils.formatdate(timestamp, usegmt=True)
        self.add_header(keyword, dt)

    def add_content(self, content:bytes, ctype:str="text/html") -> None:
        """ Add the entity headers and body for <content> with MIME type <ctype>. """
        self.add_header("Content-Type", ctype)
        self.add_header("Content-Length", str(len(content)))
        self.content = content

    def send(self) -> None:
        """ Add the status line header and the blank line ending and write everything. """
        status = f"{self.PROTOCOL_VERSION} {self}"
        header = "\r\n".join([status, *self.headers, "", ""])
        self.stream.write(header.encode('latin-1', 'strict'))
        if self.content:
            self.stream.write(self.content)

    def __str__(self) -> str:
        """ Return the status code+phrase as the string value of the response. """
        return f'{self.code} {self.code.phrase}'


class HTTPResponse_GET(HTTPResponse):
    """ Connection class specific to file GET and HEAD requests. """

    _GET_MIMETYPE = MimeTypes().guess_type

    directory: str  # Root directory for public HTTP files.

    def __init__(self, *args, directory:str=None, **kwargs):
        super().__init__(*args)
        self.directory = directory

    def __call__(self, request:HTTPRequest) -> None:
        """ Common code for GET and HEAD commands. Sends the headers required for a file, then the file itself. """
        uri_path = request.path
        file_path = self._translate_path(uri_path)
        try:
            f = open(file_path, 'rb')
        except OSError:
            raise HTTPError.NOT_FOUND(uri_path)
        with f:
            fs = os.fstat(f.fileno())
            mtime = fs.st_mtime
            if not request.modified_since(mtime):
                self.code = HTTPStatus.NOT_MODIFIED
            else:
                ctype, _ = self._GET_MIMETYPE(file_path)
                self.add_time("Last-Modified", mtime)
                self.add_content(f.read(), ctype)
            self.send()

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


class HTTPResponse_HEAD(HTTPResponse_GET):

    def add_content(self, *args) -> None:
        """ Erase any content body at the end if the command is HEAD. """
        super().add_content(*args)
        self.content = b""


class HTTPResponse_POST(HTTPResponse):
    """ Connection class specific to JSON POST requests. """

    process_action: Callable  # Main callback to process user state.

    def __init__(self, *args, process_action:Callable, **kwargs):
        super().__init__(*args)
        self.process_action = process_action

    def __call__(self, request:HTTPRequest) -> None:
        """ Start service of a POST request with JSON data and query parameters. """
        self.process_action(request.content, self.send_JSON, **request.query)

    def send_JSON(self, content:bytes) -> None:
        """ Finish a request by sending the processed JSON data. """
        self.add_content(content, "application/json")
        self.send()


class HTTPResponseContinue(HTTPResponse):
    """ Send a continue response. This cannot have a message body. """

    code = HTTPStatus.CONTINUE


class HTTPResponseError(HTTPResponse):

    def __call__(self, err:HTTPError) -> None:
        """ Send an error response and an HTML document explaining the error to the user. """
        self.add_header('Connection', 'close')
        self.code = err.args[0]
        body = err.html
        if body is not None:
            self.add_content(body)
        self.send()


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

    RESPONDERS = {'GET': HTTPResponse_GET,
                  'HEAD': HTTPResponse_HEAD,
                  'POST': HTTPResponse_POST}

    stream: RawIOBase          # Stream for reading the request and writing the response.
    log: HTTPConnectionLogger  # Callback for writing formatted log strings.
    kwargs: dict

    def __init__(self, stream:RawIOBase, addr:str, logger:Callable=sys.stderr.write, **kwargs):
        """ Add the client address as a header to each logged message. """
        self.stream = stream
        self.log = HTTPConnectionLogger(logger, addr)
        self.kwargs = kwargs

    def __call__(self) -> None:
        """ Process an HTTP connection and requests. """
        try:
            self.log("Connection opened.")
            try:
                self.handle_requests()
            except HTTPError as e:
                self.respond(HTTPResponseError, e)
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
            request = HTTPRequest(self.stream)
            method_attr = request.method
            if not method_attr:
                return
            self.log.add(request)
            cls = self.RESPONDERS[method_attr.upper()]
            if cls is None:
                raise HTTPError.NOT_IMPLEMENTED(method_attr)
            # Examine the headers and look for continue directives, then call the method.
            if request.expect_continue():
                self.respond(HTTPResponseContinue, request)
            self.respond(cls, request)
            if not request.keep_alive():
                return

    def respond(self, cls:type, *args) -> None:
        """ Create a new HTTP response from our current stream and kwargs and call it to send. """
        response = cls(self.stream, **self.kwargs)
        response(*args)
        self.log(response)

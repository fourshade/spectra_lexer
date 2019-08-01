from collections import Callable
from http import HTTPStatus
import os
from json import JSONDecoder, JSONEncoder
from mimetypes import MimeTypes
from threading import Thread

from .http import HTTPConnection, HTTPError, HTTPRequest, HTTPResponse
from .tcp import TCPServerSocket


class ResponseDict(dict):
    """ A dict subclass with response metadata that is preserved through an action call. """
    response: HTTPResponse


class JSONValidator:
    """ Transcodes and validates GUI state data submitted as JSON by HTTP. """

    decoder: JSONDecoder
    encoder: JSONEncoder
    size_limit: int     # Limit on total size of JSON data in bytes.
    char_limits: tuple  # Limits on special JSON characters.

    def __init__(self, size_limit:int=100000, char_limits:tuple=((b"{", 20),(b"[", 20))):
        """ Keep Unicode characters intact. Make sure bytes objects are converted to normal strings. """
        self.decoder = JSONDecoder()
        self.encoder = JSONEncoder(ensure_ascii=False, default=bytes.decode)
        self.size_limit = size_limit
        self.char_limits = char_limits

    def decode(self, data:bytes) -> dict:
        """ Process JSON data obtained from a client. This data could contain ANYTHING...beware! """
        if len(data) > self.size_limit:
            raise ValueError("Data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in self.char_limits:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")
        return self.decoder.decode(data.decode('utf-8'))

    def encode(self, d:dict) -> bytes:
        return self.encoder.encode(d).encode('utf-8')


class HTTPDispatcher:
    """ Dispatches methods specific to file GET and HEAD requests and JSON POST requests. """

    _GET_MIMETYPE = MimeTypes().guess_type
    _VALIDATOR = JSONValidator()

    _GET_directory: str        # Root directory for public HTTP file requests.
    _POST_processor: Callable  # External callback to process application state.

    def __init__(self, directory:str, processor:Callable):
        self._GET_directory = directory
        self._POST_processor = processor

    def __call__(self, request:HTTPRequest, response:HTTPResponse) -> None:
        """ Routes HTTP requests by method. Must be completely thread safe. """
        method_attr = request.method.upper()
        method = getattr(self, method_attr, None)
        if method is None:
            raise HTTPError.NOT_IMPLEMENTED(method_attr)
        method(request, response)

    def GET(self, request:HTTPRequest, response:HTTPResponse, head:bool=False) -> None:
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
                response.send(HTTPStatus.NOT_MODIFIED)
            else:
                ctype, _ = self._GET_MIMETYPE(file_path)
                response.add_time("Last-Modified", mtime)
                response.add_content(f.read(), ctype)
                if head:
                    response.content = b""
                response.send()

    def HEAD(self, *args) -> None:
        """ Erase any content body at the end if the command is HEAD. """
        self.GET(*args, head=True)

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
        file_path = os.path.join(self._GET_directory, *new_comps)
        # Route bare directory paths to index.html (whether or not it exists).
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")
        return file_path

    def POST(self, request:HTTPRequest, response:HTTPResponse) -> None:
        """ Process JSON and query data obtained from a client. """
        data = request.content
        d = self._VALIDATOR.decode(data)
        state = ResponseDict(d)
        state.response = response
        action = request.path.split('/')[-1]
        self._POST_processor(state, action)

    def send_result(self, changed:ResponseDict) -> None:
        """ Finish a POST response by encoding any relevant changes to JSON and send them back to the client. """
        data = self._VALIDATOR.encode(changed)
        response = changed.response
        response.add_content(data, "application/json")
        response.send()


class HTTPServer:
    """ Class for socket-based TCP/IP stream server, JSON, and communication with the view layer. """

    _dispatcher: HTTPDispatcher  # Handles each HTTP method independently.
    _logger: Callable            # Used to log all HTTP responses and errors (but not headers).
    _running: bool = True

    def __init__(self, directory:str, processor:Callable, logger:Callable):
        self._dispatcher = HTTPDispatcher(directory, processor)
        self._logger = logger

    def start(self, address:str, port:int) -> None:
        """ Make a server socket object which creates other sockets for connections and poll it on a new thread. """
        sock = TCPServerSocket(address, port)
        Thread(target=self._serve_forever, args=(sock,), daemon=True).start()

    def _serve_forever(self, sock:TCPServerSocket) -> None:
        """ Handle each request by instantiating a connection and calling it with a new thread. """
        self._running = True
        with sock:
            while self._running:
                if sock.poll():
                    stream, addr = sock.accept()
                    connection = HTTPConnection(stream, addr, self._dispatcher, self._logger)
                    Thread(target=connection, daemon=True).start()

    def shutdown(self) -> None:
        """ Halt serving and close any open sockets and files. Must be called by another thread. """
        self._running = False

    def process_done(self, *args) -> None:
        """ Called by another thread to finish a request by sending the processed state data. """
        self._dispatcher.send_result(*args)

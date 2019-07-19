from http import HTTPStatus
import os
from mimetypes import MimeTypes
from threading import Thread

from .base import GUIHTTP
from .http import HTTPConnection, HTTPError, HTTPRequest, HTTPResponse
from .tcp import TCPServerSocket
from spectra_lexer.system import CmdlineOption
from spectra_lexer.types.codec import JSONDict


class ResponseDict(JSONDict):
    """ A dict subclass with response metadata that is preserved through an action call. """
    response: HTTPResponse


class JSONValidator:
    """ Validates GUI state data submitted as JSON by HTTP. """

    size_limit: int     # Limit on total size of JSON data in bytes.
    char_limits: tuple  # Limits on special JSON characters.

    def __init__(self, size_limit:int=100000, char_limits:tuple=((b"{", 20),(b"[", 20))):
        self.size_limit = size_limit
        self.char_limits = char_limits

    def decode(self, data:bytes) -> ResponseDict:
        """ Process JSON data obtained from a client. This data could contain ANYTHING...beware! """
        if len(data) > self.size_limit:
            raise ValueError("Data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in self.char_limits:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")
        return ResponseDict.decode(data)

    def encode(self, d:ResponseDict) -> bytes:
        """ Finish a response by encoding any relevant changes to JSON and send them back to the client.
            Make sure all bytes objects are converted to normal strings before encoding. """
        for k, v in d.items():
            if isinstance(v, bytes):
                d[k] = v.decode()
        return d.encode()


class HttpServer(GUIHTTP):
    """ Class for socket-based TCP/IP stream server, JSON, and communication with the view layer. """

    _GET_MIMETYPE = MimeTypes().guess_type
    _VALIDATOR = JSONValidator()

    address: str = CmdlineOption("http-addr", default="localhost", desc="IP address or hostname for server.")
    port: int = CmdlineOption("http-port", default=80, desc="TCP port to listen for connections.")

    sock: TCPServerSocket = None  # Server socket object which creates other sockets for connections.

    def Load(self) -> None:
        self.sock = TCPServerSocket(self.address, self.port)

    def GUIHTTPServe(self) -> None:
        """ Handle each request by instantiating a connection and calling it with a new thread. """
        if self.sock.poll():
            stream, addr = self.sock.accept()
            connection = HTTPConnection(stream, addr, self.dispatch, self.SYSStatus)
            Thread(target=connection, daemon=True).start()

    def GUIHTTPShutdown(self) -> None:
        self.sock.close()

    def dispatch(self, request:HTTPRequest, response:HTTPResponse) -> None:
        """ Routes HTTP requests by method. Must be completely thread safe. """
        method_attr = request.method.upper()
        method = getattr(self, method_attr, None)
        if method is None:
            raise HTTPError.NOT_IMPLEMENTED(method_attr)
        method(request, response)

    # Methods specific to file GET and HEAD requests and JSON POST requests.

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
        file_path = os.path.join(self.HTTP_PUBLIC or os.getcwd(), *new_comps)
        # Route bare directory paths to index.html (whether or not it exists).
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, "index.html")
        return file_path

    def POST(self, request:HTTPRequest, response:HTTPResponse) -> None:
        """ Process JSON and query data obtained from a client. """
        state = self._VALIDATOR.decode(request.content)
        state.response = response
        action = request.path.split('/')[-1]
        self.VIEWAction(state, action)

    def VIEWActionResult(self, changed:ResponseDict) -> None:
        data = self._VALIDATOR.encode(changed)
        response = changed.response
        response.add_content(data, "application/json")
        response.send()

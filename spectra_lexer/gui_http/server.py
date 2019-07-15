from http import HTTPStatus
import os
from mimetypes import MimeTypes
from threading import Thread

from .base import GUIHTTP
from .http import HTTPConnection, HTTPError, HTTPRequest, HTTPResponse
from .tcp import TCPServerSocket
from spectra_lexer.system import CmdlineOption
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.view import ViewState


class HttpViewState(ViewState):
    """ Class for GUI state data submitted as JSON by HTTP. """

    SIZE_LIMIT = 100000         # No way should user JSON data be over 100 KB.
    CHAR_LIMITS = [(b"{", 20),  # Limits on special JSON characters.
                   (b"[", 20)]

    response: HTTPResponse = None

    def __init__(self, data:bytes, response:HTTPResponse) -> None:
        """ Process JSON data obtained from a client. This data could contain ANYTHING...beware! """
        self.validate(data)
        super().__init__(JSONDict.decode(data), response=response)

    @classmethod
    def validate(cls, data:bytes) -> None:
        """ Validate JSON data from an untrusted source. """
        if len(data) > cls.SIZE_LIMIT:
            raise ValueError("Data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in cls.CHAR_LIMITS:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")

    def send(self) -> None:
        """ Finish a response by encoding any relevant changes to JSON and send them back to the client.
            Make sure all bytes objects are converted to normal strings before encoding. """
        d = JSONDict(self.changed())
        for k, v in d.items():
            if isinstance(v, bytes):
                d[k] = v.decode()
        response = self.response
        response.add_content(d.encode(), "application/json")
        response.send()


class HttpServer(GUIHTTP):
    """ Class for socket-based TCP/IP stream server, JSON, and communication with the view layer. """

    _GET_MIMETYPE = MimeTypes().guess_type

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
        state = HttpViewState(request.content, response)
        self.VIEWAction(state, **request.query)

    def VIEWActionResult(self, state:HttpViewState) -> None:
        state.send()

from threading import Thread
from typing import Callable

from .base import GUIHTTP
from .http import HTTPConnection
from .tcp import TCPServerSocket
from spectra_lexer.system import CmdlineOption
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.view import ViewState


class HttpJSONDict(JSONDict):

    _SIZE_LIMIT = 100000         # No way should user JSON data be over 100 KB.
    _CHAR_LIMITS = [(b"{", 20),  # Limits on special JSON characters.
                    (b"[", 20)]

    @classmethod
    def _decode(cls, data:bytes, **kwargs) -> dict:
        """ Validate and decode JSON data from an untrusted source. """
        if len(data) > cls._SIZE_LIMIT:
            raise ValueError("Data payload too large.")
        # The JSON parser is fast, but dumb. It does naive recursion on containers.
        # The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen.
        for c, limit in cls._CHAR_LIMITS:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")
        return super()._decode(data, **kwargs)

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        """ Make sure all bytes objects are converted to normal strings before encoding. """
        for k, v in self.items():
            if isinstance(v, bytes):
                self[k] = v.decode(encoding)
        return super().encode(encoding=encoding, **kwargs)


class HttpViewState(ViewState):
    """ Class for GUI state data submitted by HTTP with extra fields. """

    action: str = ""
    response_callback: Callable = None


class HttpServer(GUIHTTP):
    """ Class for socket-based TCP/IP stream server, JSON, and communication with the view layer. """

    address: str = CmdlineOption("http-addr", default="localhost", desc="IP address or hostname for server.")
    port: int = CmdlineOption("http-port", default=80, desc="TCP port to listen for connections.")

    sock: TCPServerSocket = None  # Server socket object which creates other sockets for connections.

    def Load(self) -> None:
        """ Create the window and connect all GUI controls. """
        self.sock = TCPServerSocket(self.address, self.port)

    def GUIHTTPServe(self) -> None:
        """ Handle each request by instantiating a connection and calling it with a new thread. """
        if self.sock.poll():
            connection = HTTPConnection(*self.sock.accept(), self.SYSStatus,
                                        directory=self.HTTP_PUBLIC, process_action=self.process)
            Thread(target=connection, daemon=True).start()

    def GUIHTTPShutdown(self) -> None:
        self.sock.close()

    def process(self, data:bytes, response_callback:Callable, **query):
        """ Process JSON and query data obtained from a client. This data could contain ANYTHING...beware! """
        d = HttpJSONDict.decode(data)
        state = HttpViewState(d, response_callback=response_callback)
        self.VIEWAction(state.action, state, **query)

    def VIEWActionResult(self, state:HttpViewState) -> None:
        """ Encode any relevant changes to JSON and send them back to the client with the callback. """
        d = HttpJSONDict(state.changed())
        state.response_callback(d.encode())

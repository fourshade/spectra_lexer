from typing import Callable

from .base import GUIHTTP
from .server import SpectraHTTPServer
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.view import ViewState


class HttpData(JSONDict):

    _SIZE_LIMIT = 1000000  # No way should user JSON data be over 1 MB.

    @classmethod
    def _decode(cls, data:bytes, **kwargs) -> dict:
        """ Perform a basic data size check before parsing. """
        if len(data) > cls._SIZE_LIMIT:
            raise ValueError("Data payload too large.")
        return super()._decode(data, **kwargs)

    def encode(self, *, encoding:str='utf-8', **kwargs) -> bytes:
        """ Make sure all bytes objects are converted to normal strings before JSON encoding. """
        for k, v in self.items():
            if isinstance(v, bytes):
                self[k] = v.decode(encoding)
        return super().encode(encoding=encoding, **kwargs)


class HttpState(ViewState):

    action: str = ""
    req_call: Callable = None

    @classmethod
    def from_request(cls, data:bytes, req_call:Callable):
        """ Process JSON data obtained from a client request. Save the callback so we don't lose it. """
        d = HttpData.decode(data)
        return cls(d, req_call=req_call)

    def send(self) -> None:
        """ Encode any relevant changes to JSON and send them back to the client with the callback. """
        data = HttpData(self.changed()).encode()
        self.req_call(data)


class HttpView(GUIHTTP):
    """ Top-level component for the HTTP server. Handles JSON and communication with the view layer. """

    _ADDRESS = "localhost", 80

    def GUIHTTPServe(self) -> int:
        httpd = SpectraHTTPServer(self._ADDRESS, callback=self.process_request, directory=self._HTTP_PUBLIC)
        httpd.serve_forever()
        return 0

    def process_request(self, data:bytes, req_call:Callable) -> None:
        state = HttpState.from_request(data, req_call)
        self.VIEWAction(state.action, state)

    def VIEWActionResult(self, state:HttpState) -> None:
        state.send()

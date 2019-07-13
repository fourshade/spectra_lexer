from typing import Callable

from .base import GUIHTTP
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


class HttpView(GUIHTTP):
    """ Interface to handle JSON and communication with the view layer. """

    def GUIHTTPRequest(self, data:bytes, response_callback:Callable):
        """ Process JSON data obtained from a client. This data could contain ANYTHING...beware! """
        d = HttpJSONDict.decode(data)
        state = HttpViewState(d, response_callback=response_callback)
        self.VIEWAction(state.action, state)

    def VIEWActionResult(self, state:HttpViewState) -> None:
        """ Encode any relevant changes to JSON and send them back to the client with the callback. """
        d = HttpJSONDict(state.changed())
        state.response_callback(d.encode())

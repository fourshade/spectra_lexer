from typing import Callable

from .base import GUIHTTP
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.view import ViewState


class HttpState(ViewState):
    """ Class for GUI state data submitted by HTTP with extra fields. """

    action: str = ""
    response_callback: Callable = None


class HttpView(GUIHTTP):
    """ Interface to handle JSON and communication with the view layer. """

    _SIZE_LIMIT = 1000000        # No way should user JSON data be over 1 MB.
    _CHAR_LIMITS = [(b"{", 20),  # Limits on special JSON characters.
                    (b"[", 20)]

    def GUIHTTPRequest(self, data:bytes, response_callback:Callable):
        """ Validate and process JSON data obtained from a client. This data could contain ANYTHING...beware! """
        self.check_size(data)
        self.check_chars(data)
        d = JSONDict.decode(data)
        state = HttpState(d, response_callback=response_callback)
        self.VIEWAction(state.action, state)

    def check_size(self, data:bytes) -> None:
        """ Perform a basic data size check. """
        if len(data) > self._SIZE_LIMIT:
            raise ValueError("Data payload too large.")

    def check_chars(self, data:bytes) -> None:
        """ The JSON parser is fast, but dumb. It does naive recursion on containers.
            The stack can be overwhelmed by a long sequence of '{' and/or '[' characters. Do not let this happen. """
        for c, limit in self._CHAR_LIMITS:
            if data.count(c) > limit:
                raise ValueError("Too many containers.")

    def VIEWActionResult(self, state:HttpState, encoding:str='utf-8') -> None:
        """ Encode any relevant changes to JSON and send them back to the client with the callback.
            Make sure all bytes objects are converted to normal strings before encoding. """
        d = JSONDict(state.changed(), encoding=encoding)
        for k, v in d.items():
            if isinstance(v, bytes):
                d[k] = v.decode(encoding)
        state.response_callback(d.encode())

import os
from typing import Callable

from spectra_lexer.core import Command
from spectra_lexer.view import VIEW


class GUIHTTP(VIEW):

    HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")  # Root directory for public HTTP file service.

    @Command
    def GUIHTTPServe(self) -> int:
        """ Handle HTTP requests indefinitely. """
        raise NotImplementedError

    @Command
    def GUIHTTPAction(self, data:bytes, response_callback:Callable, **query) -> None:
        """ Process action and state data obtained from a client request. """
        raise NotImplementedError

import os

from spectra_lexer.core import Command
from spectra_lexer.view import VIEW


class GUIHTTP(VIEW):

    HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")  # Root directory for public HTTP file service.

    @Command
    def GUIHTTPServe(self) -> int:
        """ Handle HTTP requests indefinitely. """
        raise NotImplementedError

    @Command
    def GUIHTTPShutdown(self) -> None:
        """ Close any open sockets and files. """
        raise NotImplementedError

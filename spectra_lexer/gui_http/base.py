import os

from spectra_lexer.core import Command
from spectra_lexer.view import VIEW


class GUIHTTP(VIEW):

    _HTTP_PUBLIC = os.path.join(os.path.split(__file__)[0], "public")

    @Command
    def GUIHTTPServe(self) -> int:
        raise NotImplementedError

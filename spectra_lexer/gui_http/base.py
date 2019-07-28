from spectra_lexer.core import Command


class GUIHTTP:

    @Command
    def GUIHTTPServe(self) -> int:
        """ Handle HTTP requests indefinitely. """
        raise NotImplementedError

    @Command
    def GUIHTTPShutdown(self) -> None:
        """ Close any open sockets and files. """
        raise NotImplementedError

from spectra_lexer.core import Command


class SYSControl:
    """ Simple interface definition for general system commands with no specific category. """

    @Command
    def status(self, status:str) -> None:
        """" Display a plaintext status message (non-error). """
        raise NotImplementedError

    @Command
    def exit(self) -> None:
        """ Exit the application entirely. """
        raise NotImplementedError

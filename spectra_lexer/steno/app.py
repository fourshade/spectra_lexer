from time import time

from spectra_lexer import steno
from spectra_lexer.system import SYSConsole
from spectra_lexer.system.app import SystemApplication


class StenoApplication(SystemApplication):
    """ Abstract base application class with all required components. """

    def _class_paths(self) -> list:
        return [*super()._class_paths(), steno]


class _ConsoleApplication(StenoApplication):
    """ Abstract base application class for console operations from a terminal. """

    DESCRIPTION = "Run commands directly from console."

    def _start(self, **kwargs) -> str:
        return self.call(SYSConsole.open, **kwargs)

    def _eval(self, text_in:str) -> str:
        return self.call(SYSConsole.input, text_in)

    def _out(self, text_out:str) -> None:
        print(text_out, end='')


class StenoConsoleApplication(_ConsoleApplication):
    """ Application class for an interactive terminal. """

    def run(self) -> int:
        """ Start the console for interactive operation in the terminal. """
        super().run()
        self._out(self._start(interactive=True))
        self._repl()
        return 0

    def _repl(self) -> None:
        while True:
            try:
                self._out(self._eval(input()))
            except KeyboardInterrupt:
                self._out("KeyboardInterrupt\n")


class _BatchApplication(_ConsoleApplication):
    """ Subclass this to run a single console command in batch mode. """

    COMMAND = ""  # Batch command to run on start.

    def run(self) -> int:
        """ Run the given command in batch mode (timing its execution) and exit. """
        super().run()
        self._start(interactive=False)
        start_time = time()
        self._out("Operation started.\n")
        self._out(self._eval(self.COMMAND))
        self._out(f"Operation done in {time() - start_time:.1f} seconds.\n")
        return 0


class StenoAnalyzeApplication(_BatchApplication):
    DESCRIPTION = "Run the lexer on every item in a JSON steno translations dictionary."
    COMMAND = "rules_save(analyzer_make_rules())"


class StenoIndexApplication(_BatchApplication):
    DESCRIPTION = "Analyze a translations file and index each translation by the rules it uses."
    COMMAND = "index_save(analyzer_make_index())"

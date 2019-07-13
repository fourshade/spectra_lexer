from time import time

from .base import LX
from spectra_lexer import resource, steno, system
from spectra_lexer.core.app import Application


class StenoApplication(Application, LX):
    """ Base application class with all required components for interactive console operations. """

    def _class_paths(self) -> list:
        return [system, resource, steno]

    def run(self) -> None:
        """ Run the console in an interactive read-eval-print loop. """
        self.SYSConsoleOpen()
        while True:
            self.SYSConsoleInput(input())


class _BatchApplication(StenoApplication):
    """ Base application class for batch console operations. """

    COMMAND = ""

    def run(self) -> int:
        """ Run the main command in the console in batch mode and time its execution. """
        start_time = time()
        print("Operation started...")
        self.SYSConsoleOpen(interactive=False)
        self.SYSConsoleInput(self.COMMAND)
        print(f"Operation done in {time() - start_time:.1f} seconds.")
        return 0


class StenoAnalyzeApplication(_BatchApplication):
    """ Runs the lexer on every item in a JSON steno translations dictionary. """

    COMMAND = "RSRulesSave(LXLexerQueryAll())"


class StenoIndexApplication(_BatchApplication):
    """ Analyzes translations files and creates indices from them. """

    COMMAND = "RSIndexSave(LXLexerMakeIndex())"

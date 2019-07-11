from .base import LX
from spectra_lexer import resource, steno, system
from spectra_lexer.core.app import Application


class StenoApplication(Application, LX):
    """ Base application class with all required components for interactive console operations. """

    def _class_paths(self) -> list:
        return [system, resource, steno]

    def run(self) -> int:
        return self.SYSConsoleRepl()


class StenoAnalyzeApplication(StenoApplication):
    """ Runs the lexer on every item in a JSON steno translations dictionary. """

    def run(self) -> int:
        return self.SYSConsoleBatch("RSRulesSave(LXLexerQueryAll())")


class StenoIndexApplication(StenoApplication):
    """ Analyzes translations files and creates indices from them. """

    def run(self) -> int:
        return self.SYSConsoleBatch("RSIndexSave(LXLexerMakeIndex())")

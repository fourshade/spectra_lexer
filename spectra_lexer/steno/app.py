from .base import LX
from spectra_lexer import resource, steno, system
from spectra_lexer.core.app import Application


class StenoApplication(Application, LX):
    """ Base application class with all required components for interactive console operations. """

    DESCRIPTION = "Run commands interactively from console."

    def _class_paths(self) -> list:
        return [system, resource, steno]

    def run(self) -> int:
        return self.SYSConsoleRepl()


class StenoAnalyzeApplication(StenoApplication):

    DESCRIPTION = "Run the lexer on every item in a JSON steno translations dictionary."

    def run(self) -> int:
        return self.SYSConsoleBatch("RSRulesSave(LXAnalyzerMakeRules())")


class StenoIndexApplication(StenoApplication):

    DESCRIPTION = "Analyze a translations file and index each translation by the rules it uses."

    def run(self) -> int:
        return self.SYSConsoleBatch("RSIndexSave(LXAnalyzerMakeIndex())")


StenoApplication.set_entry_point("console")
StenoAnalyzeApplication.set_entry_point("analyze")
StenoIndexApplication.set_entry_point("index")

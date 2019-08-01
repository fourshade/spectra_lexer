from time import time

from .view import ViewManager
from spectra_lexer.core import Application, Engine, SpectraCore, ThreadedEngineGroup
from spectra_lexer.resource import ResourceManager
from spectra_lexer.steno import StenoEngine


class _StenoApplication(Application):
    """ Base application class with all required system and steno components. """

    def _build_components(self) -> list:
        return [SpectraCore(), ResourceManager(), StenoEngine(), ViewManager()]

    def batch(self, command:str) -> int:
        """ Run a command in the console in batch mode and time its execution. """
        start_time = time()
        print("Operation started...")
        self.COREConsoleOpen(interactive=False)
        self.COREConsoleInput(command)
        print(f"Operation done in {time() - start_time:.1f} seconds.")
        return 0

    def repl(self) -> None:
        """ Run the console in an interactive read-eval-print loop. """
        self.COREConsoleOpen()
        while True:
            text = input()
            if text.startswith("exit()"):
                break
            self.COREConsoleInput(text)


class StenoConsoleApplication(_StenoApplication):
    """ Runs interactive console operations. """

    def run(self) -> int:
        self.repl()
        return 0


class StenoAnalyzeApplication(_StenoApplication):
    """ Runs the lexer on every item in a JSON steno translations dictionary. """

    def run(self) -> int:
        return self.batch("RSRulesSave(LXAnalyzerMakeRules())")


class StenoIndexApplication(_StenoApplication):
    """ Analyzes translations files and creates indices from them. """

    def run(self) -> int:
        return self.batch("RSIndexSave(LXAnalyzerMakeIndex())")


class ViewApplication(_StenoApplication):
    """ Abstract base class for multi-threaded interactive steno applications. """

    def _build_interface(self) -> list:
        """ We run the primary task on the main thread, and the other layers on a worker thread. """
        raise NotImplementedError

    def _build_engine(self, components:list, **kwargs) -> Engine:
        """ For multi-threaded applications, there is a separate component list for each thread. """
        main_group = self._build_interface()
        worker_group = components[:]
        components += main_group
        return ThreadedEngineGroup(main_group, worker_group, **kwargs)

""" Main module and entry point for batch operations on Spectra. """

from time import time

from .app import Application
from spectra_lexer import core, steno


class BatchApplication(Application):
    """ Simple shell class for calling arbitrary engine commands from the command line. """
    INPUT: str = ""
    COMMAND: str = ""
    PIPES = ()

    input_dict: dict = {}  # Translations dict for mass queries.

    def __init__(self, *classes):
        super().__init__(core, steno.basic, *classes)
        for on, to in self.PIPES:
            self._commands[on].append((self, "pipe", to, {}))
        self._commands["set_dict_"+self.INPUT].append((self, "set_input", None, {}))

    def set_input(self, d:dict) -> None:
        self.input_dict = d

    def pipe(self, *args) -> tuple:
        """ Echo the results of one command immediately to another. """
        return args

    def run(self, *args) -> int:
        """ Start the timer and run the app. """
        s_time = time()
        print(f"Operation started.")
        self.call(self.COMMAND, self.input_dict)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0


class BatchAnalyzeApplication(BatchApplication):
    DESCRIPTION = "run the lexer on every item in a JSON steno translations dictionary."
    INPUT = "translations"
    COMMAND = "lexer_query_all"
    PIPES = [("new_analysis", "rules_save")]


class BatchIndexApplication(BatchApplication):
    DESCRIPTION = "analyze a translations file and index each translation by the rules it uses."
    INPUT = "translations"
    COMMAND = "lexer_make_index"
    PIPES = [("new_index", "index_save")]

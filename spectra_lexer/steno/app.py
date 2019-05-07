""" Main module and entry point for batch operations on Spectra. """

from time import time

from spectra_lexer import system, steno
from spectra_lexer.core import Application


class StenoApplication(Application):
    """ Simple shell class for calling engine commands from the command line in batch. """

    DESCRIPTION = "run a command set directly from console."
    CLASS_PATHS = [system, steno.basic]
    COMMAND: str = ""

    def run(self) -> int:
        """ Start the timer and run the <COMMAND> in the console. """
        s_time = time()
        print(f"Operation started.")
        self.call("console_input", self.COMMAND)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0


class StenoAnalyzeApplication(StenoApplication):
    DESCRIPTION = "run the lexer on every item in a JSON steno translations dictionary."
    COMMAND = "rules_save(analyzer_make_rules())"


class StenoIndexApplication(StenoApplication):
    DESCRIPTION = "analyze a translations file and index each translation by the rules it uses."
    COMMAND = "index_save(analyzer_make_index())"

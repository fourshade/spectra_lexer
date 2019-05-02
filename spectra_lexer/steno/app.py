""" Main module and entry point for batch operations on Spectra. """

from spectra_lexer import core, steno
from spectra_lexer.app import Application


class StenoApplication(Application):
    """ Simple shell class for calling basic engine commands from the command line. """

    CLASS_PATHS = [core, steno.basic]
    COMMAND: str

    translations = resource("translations", {})

    def run(self, *args) -> int:
        """ Run the class command set with the translations as input. """
        self.engine_call("batch_run", self.translations, self.COMMAND)
        return 0


class StenoAnalyzeApplication(StenoApplication):
    DESCRIPTION = "run the lexer on every item in a JSON steno translations dictionary."
    COMMAND = "lexer_query_all | rules_save"


class StenoIndexApplication(StenoApplication):
    DESCRIPTION = "analyze a translations file and index each translation by the rules it uses."
    COMMAND = "lexer_make_index | index_save"

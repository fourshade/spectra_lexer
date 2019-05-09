""" Main entry point for console operations on Spectra. """

import sys

from spectra_lexer import system, steno
from spectra_lexer.system import ConsoleApplication


class StenoApplication(ConsoleApplication):
    """ Simple shell class for running the steno program from the command line. """
    CLASS_PATHS = [system, steno.basic]
    CMDLINE_ARGS: list = []

    def __init__(self):
        """ Batch operation subclasses may add optional args to the command line before parsing. """
        sys.argv += self.CMDLINE_ARGS
        super().__init__()


class StenoAnalyzeApplication(StenoApplication):
    DESCRIPTION = "run the lexer on every item in a JSON steno translations dictionary."
    CMDLINE_ARGS = ["--cmd=rules_save(analyzer_make_rules())"]


class StenoIndexApplication(StenoApplication):
    DESCRIPTION = "analyze a translations file and index each translation by the rules it uses."
    CMDLINE_ARGS = ["--cmd=index_save(analyzer_make_index())"]

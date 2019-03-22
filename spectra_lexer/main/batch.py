""" Main module and entry point for batch operations on Spectra. """

from time import time

from .app import Application
from spectra_lexer import core, steno


class BatchApplication(Application):
    """ Simple shell class for calling arbitrary engine commands from the command line. """

    def __init__(self, *classes):
        super().__init__(core, steno.basic, *classes)

    def run(self, *args) -> int:
        """ Run the engine command in the arguments and print the execution time. """
        s_time = time()
        print(f"Operation started.")
        self.call(*args)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

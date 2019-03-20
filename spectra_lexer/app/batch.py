""" Module for the batch components of Spectra. These handle bulk data operations. """

from time import time

from .base import Application
from spectra_lexer import core, steno


class BatchApplication(Application):
    """ Batch operations class for working with arbitrary engine commands. """

    def __init__(self, *classes):
        super().__init__(core, steno.basic, *classes)

    def run(self, *args) -> int:
        """ Run the engine command in the arguments and print the execution time. """
        s_time = time()
        print(f"Operation started.")
        self.call(*args)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

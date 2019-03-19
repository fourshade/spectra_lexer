""" Module for the batch components of Spectra. These handle bulk data operations. """

from time import time

from spectra_lexer import Component


class BatchProcessor(Component):
    """ Batch operations class for working with arbitrary engine commands. """

    @on("run")
    def run(self, *args) -> int:
        """ Run the engine command in the arguments and print the execution time. """
        s_time = time()
        print(f"Operation started.")
        self.engine_call(*args)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

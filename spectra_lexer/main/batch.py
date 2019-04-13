""" Main module and entry point for batch operations on Spectra. """

from time import time

from .app import Application
from spectra_lexer import Component, core, steno
from spectra_lexer.base import ComponentMeta


class BatchApplication(Application):
    """ Simple shell class for calling arbitrary engine commands from the command line. """

    def __init__(self, *classes):
        super().__init__(core, steno.basic, *classes)

    def run(self, cmd, *pipes) -> int:
        """ Run the engine command in the arguments, handle any pipes, and print the execution time. """
        if pipes:
            # Pipes are simply pairs of commands where one feeds its return value directly into the next.
            # If there are pipes, create and connect a component dynamically to handle them.
            methods = {on: Component.on(on, pipe_to=to)(staticmethod(lambda x: x)) for on, to in pipes}
            cmp = ComponentMeta("Pipe", (Component,), methods)()
            self.connect(cmp)
        s_time = time()
        print(f"Operation started.")
        self.call(*cmd)
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

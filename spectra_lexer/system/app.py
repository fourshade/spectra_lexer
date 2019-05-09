from functools import partial
from time import time

from spectra_lexer.core import Application, Component


class ConsoleTerminal(Component):
    """ Component for console operations from a terminal. """

    command = resource("cmdline:cmd", "", desc="Batch command to run on start.")

    @on("terminal_run")
    def run(self) -> int:
        """ If a command was given, run it in batch mode (timing its execution) and exit.
            Otherwise, start the console for interactive operation in the terminal. """
        if self.command:
            start_time = time()
            self._start(interactive=False)
            self.output("Operation started.\n")
            self._send(self.command)
            self.output(f"Operation done in {time() - start_time:.1f} seconds.\n")
        else:
            self._start(interactive=True)
            while True:
                self._send(input())
        return 0

    def _start(self, **kwargs) -> None:
        self.engine_call("console_start", **kwargs)

    def _send(self, text:str) -> None:
        self.engine_call("console_input", text)

    output = on("new_console_output")(partial(print, end=''))


class ConsoleApplication(Application):
    """ Simple shell class for running a console from the command line. """

    DESCRIPTION = "run commands directly from console."

    def _class_paths(self) -> list:
        return [ConsoleTerminal]

    def run(self) -> int:
        return self.call("terminal_run")

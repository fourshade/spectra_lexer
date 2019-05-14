from code import InteractiveInterpreter
import sys
from time import time
from typing import Callable, Iterator

from .tools import AttrRedirector


class ConsoleIO:
    """ String-based IO interface for an interpreter console with an opening message and prompts. """

    ps1: str = ">>> "  # Default input prompt.
    ps2: str = "... "  # Input prompt when more lines are needed.

    START_MSG: str = f"Spectra Console - Python {sys.version}\n" \
                     f"Type 'dir()' to see a list of engine commands and other globals.\n{ps1}"

    _console = InteractiveInterpreter  # Executes Python code in interactive line-by-line mode.
    _in_buffer: str = ""               # Holds characters from multi-line inputs until finished.
    _out_buffer: list                  # Output text buffer, used like StringIO

    def __init__(self, locals_ns:dict, *, interactive:bool=True):
        """ The opening message and prompts are only shown in interactive mode. """
        self._console = InteractiveInterpreter(locals_ns)
        if interactive:
            buf = [self.START_MSG]
        else:
            buf = []
            self.ps1 = self.ps2 = ""
        self._out_buffer = buf
        self.write = buf.append

    def input(self, text_in:str) -> None:
        """ When a new line of text is sent, add it to the input buffer and run it if it makes a complete statement.
            Redirect the standard output streams to our output buffer during execution. """
        source = self._in_buffer + text_in
        with AttrRedirector(sys, stdout=self, stderr=self):
            more = self._console.runsource(source)
        self._in_buffer = (source + "\n") * more
        self.write(self.ps2 if more else self.ps1)

    def output(self) -> str:
        """ Join and return all output text in the buffer, then reset it back to empty. """
        buf = self._out_buffer
        value = "".join(buf)
        buf.clear()
        return value

    def run_batch(self, *lines:str) -> Iterator[str]:
        """ Run lines of Python code in batch mode. Track and print the total execution time. """
        start_time = time()
        yield "Operation started...\n"
        for cmd in lines:
            self.input(cmd)
            yield self.output()
        yield f"Operation done in {time() - start_time:.1f} seconds.\n"

    def run_repl(self, input_cb:Callable[[], str]) -> Iterator[str]:
        """ Run a REPL in the console, taking input lines from the callback. """
        while True:
            try:
                yield self.output()
                self.input(input_cb())
            except KeyboardInterrupt:
                self.write("KeyboardInterrupt\n")

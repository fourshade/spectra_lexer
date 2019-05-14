from code import InteractiveInterpreter
from io import StringIO
import sys

from .tools import AttrRedirector


class ConsoleIO(StringIO):
    """ String-based IO interface for an interpreter console with an opening message and prompts. """

    ps1: str = ">>> "  # Default input prompt.
    ps2: str = "... "  # Input prompt when more lines are needed.

    START_MSG: str = f"Spectra Console - Python {sys.version}\n" \
                     f"Type 'dir()' to see a list of engine commands and other globals.\n{ps1}"

    _console = InteractiveInterpreter  # Executes Python code in interactive line-by-line mode.
    _in_buffer: str = ""               # Holds characters from multi-line inputs until finished.

    def __init__(self, console:InteractiveInterpreter, *, interactive:bool=True):
        """ The opening message and prompts are only shown in interactive mode. """
        super().__init__()
        self._console = console
        if interactive:
            self.write(self.START_MSG)
        else:
            self.ps1 = self.ps2 = ""

    def input(self, text_in:str) -> None:
        """ When a new line of text is sent, add it to the input buffer and run it if it makes a complete statement.
            Redirect the standard output streams to our output buffer during execution. """
        source = self._in_buffer + text_in
        with AttrRedirector(sys, stdout=self, stderr=self):
            more = self._console.runsource(source)
        self._in_buffer = (source + "\n") * more
        self.write(self.ps2 if more else self.ps1)

    def output(self) -> str:
        """ Return all output text in the buffer and truncate it back to empty. """
        value = self.getvalue()
        self.seek(0)
        self.truncate()
        return value

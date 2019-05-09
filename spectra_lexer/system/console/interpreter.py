from code import InteractiveInterpreter
from io import StringIO
import sys

from .tools import AttrRedirector
from spectra_lexer.types import polymorph_index


ConsoleTypes = use_if_interactive = polymorph_index()


@use_if_interactive(False)
class Console(InteractiveInterpreter):
    """ Terminal-based interpreter console with redirectable output streams and display hook. """

    START_MSG: str = "Spectra Console - BATCH MODE\n"

    def __init__(self, d_locals:dict, **overrides):
        super().__init__(d_locals)
        # Execute a dummy statement to add the __builtins__ module to locals.
        exec("pass", d_locals)
        # Each keyword argument is an object that should override __builtins__ at the top level.
        d_locals["__builtins__"].update(overrides)

    def run(self, text_in:str) -> str:
        """ Execute a string of input text while redirecting the standard streams to a buffer we can return. """
        if text_in is None:
            # Return the startup sequence if the input text is None.
            return self.START_MSG
        output = StringIO()
        with AttrRedirector(sys, displayhook=self.display, stdout=output, stderr=output):
            self._run(text_in)
        return output.getvalue()

    def _run(self, text_in:str) -> None:
        """ In batch mode, send any string straight to the interpreter as an executable command. """
        self.runsource(text_in)

    def display(self, value:object) -> None:
        """ Like the normal console, show the repr of any return value on a new line, or nothing at all for None. """
        if value is not None:
            self.write(f"{value!r}\n")
        # Unlike the normal console, save the last value under _ in locals rather than globals.
        # It is too easy to step on other usages of _ (such as gettext) when saving to globals.
        self.locals["_"] = value


@use_if_interactive(True)
class InteractiveConsole(Console):
    """ Interactive terminal console with an opening message and prompts. """

    PS1 = ">>> "
    PS2 = "... "
    START_MSG = f"Spectra Console - Python {sys.version}\n" \
                f"Type 'dir()' to see a list of engine commands and other globals.\n{PS1}"

    buffer = ""

    def _run(self, text_in:str) -> None:
        """ When a new line of input is entered, add it to the buffer and run it if it forms a complete statement. """
        self.buffer += text_in
        try:
            if not self.runsource(self.buffer):
                self.buffer = ""
            else:
                self.buffer += "\n"
        except KeyboardInterrupt:
            self.write(f"KeyboardInterrupt\n")
            self.buffer = ""
        self.write(self.PS2 if self.buffer else self.PS1)

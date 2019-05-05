from code import InteractiveConsole
from functools import partial
import sys
from traceback import TracebackException
from typing import Callable

from spectra_lexer.core import Component


class SpectraConsole(InteractiveConsole):
    """ Interpreter console with redirectable output. """

    def __init__(self, d_locals:dict, output_cb:Callable):
        super().__init__(d_locals)
        self.write = output_cb

    def send(self, text_in:str) -> None:
        """ Process a line of input while redirecting the interactive display to our callback. """
        saved, sys.displayhook = sys.displayhook, self.displayhook
        self._send(text_in)
        sys.displayhook = saved

    def _send(self, text_in:str) -> None:
        """ When a command sends a new line of input, push to the console. """
        more = 0
        try:
            self.write(text_in + "\n")
            more = self.push(text_in)
        except KeyboardInterrupt:
            self.write("\nKeyboardInterrupt\n")
            self.resetbuffer()
        self.write("... " if more else ">>> ")

    def displayhook(self, value) -> None:
        """ Like the normal console, show the repr of any return value on a new line, or nothing at all for None. """
        if value is not None:
            self.write(f"{value!r}\n")
        # Unlike the normal console, save the last value under _ in locals rather than globals.
        # It is too easy to step on other usages of _ (such as gettext) when saving to globals.
        self.locals["_"] = value


class ConsoleManager(Component):
    """ Component for engine and system interpreter operations.
        Handles the most fundamental operations of the system, including status and exceptions. """

    debug_vars = resource("debug", {})  # Variables to load on interpreter startup as globals.

    _console: SpectraConsole = None  # Main interpreter console.

    @on("console_input")
    def send(self, text:str) -> None:
        """ Send a new string of text to the interpreter console.
            If not started, start it with the current vars dict and write the startup sequence. """
        if self._console is None:
            d = self.debug_vars.copy()
            for k in d.get("commands", ()):
                d[k] = partial(self.engine_call, k)
            callback = partial(self.engine_call, "new_console_output")
            self._console = SpectraConsole(d, callback)
            callback(f"Python {sys.version}\n"
                     f"SPECTRA DEBUG CONSOLE - Current global objects:\n"
                     f"{[*self.debug_vars]}\n"
                     f"Type 'list(commands)' to see a list of engine commands.\n")
        self._console.send(text)

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console by default. """
        print(f"SPECTRA: {msg}")

    @on("exception")
    def exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to stderr, if possible. Return the exception if unsuccessful. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            sys.stderr.write(tb_text)
        except Exception as e:
            return e

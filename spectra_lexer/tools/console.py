from code import InteractiveConsole
import sys
from functools import partial
from typing import Callable

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class DialogConsole(InteractiveConsole):
    """ Interpreter console with main output directed to a GUI dialog. """

    has_started: bool = False  # Has the dialog started and sent the first message?

    def __init__(self, locals:dict, output_cb:Callable):
        super().__init__(locals)
        self.write = output_cb

    def send(self, text_in:str) -> None:
        """ When the dialog sends a new line of input, push to the console. """
        more = 0
        if not self.has_started:
            # Write the startup sequence on first send. """
            self.write(f"Python {sys.version}\n"
                       f"SPECTRA DEBUG CONSOLE - Current global objects and options:\n"
                       f"{[*self.locals]}\n")
            sys.displayhook = self.output
            self.has_started = True
        try:
            self.write(text_in + "\n")
            more = self.push(text_in)
        except KeyboardInterrupt:
            self.write("\nKeyboardInterrupt\n")
            self.resetbuffer()
        self.write("... " if more else ">>> ")

    def output(self, value) -> None:
        """ Like the normal console, show the repr of any return value on a new line, or nothing at all for None. """
        if value is not None:
            self.write(f"{value!r}\n")


class ConsoleTool(Component):
    """ Component for interactive engine and system interpreter operations. """

    console_menu = Resource("menu", "Debug:Open Console...", ["console_tool_open"])

    _console: DialogConsole = None  # Main interpreter console.
    _console_vars: dict = {}        # Variables to load on interpreter startup.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the interpreter globals dict with all debug variables. """
        self._console_vars = dvars

    @on("console_tool_open", pipe_to="new_dialog")
    def open(self) -> tuple:
        """ Start the interpreter console with the current vars dict and show the initial generated text in a dialog.
            If it already is started, just show the dialog again with the current text contents. """
        if self._console is None:
            output_cb = partial(self.engine_call, "new_dialog_message", "console")
            self._console = DialogConsole(self._console_vars, output_cb)
        return "console", ["console_tool_send"]

    send = on("console_tool_send")(delegate_to("_console"))

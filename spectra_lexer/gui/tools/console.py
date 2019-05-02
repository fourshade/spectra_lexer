from code import InteractiveConsole
import sys
from typing import Callable, Union

from spectra_lexer import Component


class DialogConsole(InteractiveConsole):
    """ Interpreter console with main output directed to a GUI dialog. """

    has_started: bool = False  # Has the dialog started and sent the first message?

    def send(self, text_in:Union[str, Callable]) -> None:
        """ When the dialog sends a new line of input, push to the console. """
        more = 0
        if not self.has_started:
            # Set the callback and write the startup sequence on first send.
            self.write = text_in
            text_in = ""
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

    m_console = resource("menu:Debug:Open Console...", ["console_tool_open"])
    debug_vars = resource("debug", {}, desc="Variables to load on interpreter startup as globals.")

    _console: DialogConsole = None  # Main interpreter console.

    @on("console_tool_open")
    def open(self) -> None:
        """ Start the interpreter console with the current vars dict and show the initial generated text in a dialog.
            If it already is started, just show the dialog again with the current text contents. """
        if self._console is None:
            self._console = DialogConsole(self.debug_vars)
        self.open_dialog(self._console.send)

    def open_dialog(self, callback) -> None:
        raise NotImplementedError

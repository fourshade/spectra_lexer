from code import InteractiveConsole
import sys

from .console_dialog import ConsoleDialog
from spectra_lexer import Component

# Banner containing the Python version after formatting once, and the locals dict after formatting twice.
_BANNER_FORMAT = f"Python {sys.version}\nSPECTRA DEBUG CONSOLE - Current global objects and options:\n{{}}\n"


class ConsoleTool(Component):
    """ Component for interactive engine and system interpreter operations. """

    console_menu = Resource("menu", "Tools:Open Console...", ["console_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    console: InteractiveConsole = None  # Main interpreter console.
    dialog: ConsoleDialog = None        # Currently active interpreter dialog window.
    console_vars: dict = {}             # Variables to load on interpreter startup.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the interpreter globals dict with all debug variables. """
        self.console_vars = dvars

    @on("console_dialog_open")
    def open(self) -> None:
        """ Start the interpreter console with the current vars dict and show the initial generated text in a dialog.
            If it already is started, just show the dialog again with the current text contents. """
        if self.dialog is None:
            self.dialog = ConsoleDialog(self.window, self.send)
        if self.console is None:
            self.console = InteractiveConsole(self.console_vars)
            self.console.write = self.dialog.add_text
            self.console.write(_BANNER_FORMAT.format(list(self.console_vars)))
            sys.displayhook = self.output
            self.send()
        self.dialog.show()

    def send(self, text_in:str="") -> None:
        """ When the dialog sends a new line of input, push to the console. """
        more = 0
        try:
            self.console.write(text_in + "\n")
            more = self.console.push(text_in)
        except KeyboardInterrupt:
            self.console.write("\nKeyboardInterrupt\n")
            self.console.resetbuffer()
        self.console.write("... " if more else ">>> ")

    def output(self, value) -> None:
        """ Like the normal console, show the repr of any return value on a new line, or nothing at all for None. """
        if value is not None:
            self.console.write(f"{value!r}\n")

from code import InteractiveConsole
import sys

from .console_dialog import ConsoleDialog
from spectra_lexer import Component
from spectra_lexer.utils import str_prefix

# Banner containing the Python version after formatting once, and the locals dict after formatting twice.
_BANNER_FORMAT = f"Python {sys.version}\nSPECTRA DEBUG CONSOLE - Current global objects and options:\n{{}}\n"


class ConsoleTool(Component):
    """ Component for interactive engine and system interpreter operations. """

    console_menu = Resource("menu", "Tools:Open Console...", ["console_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    console: InteractiveConsole = None  # Main interpreter console.
    dialog: ConsoleDialog = None        # Currently active interpreter dialog window.
    console_vars: dict = {}             # Variables to load on interpreter startup.

    @on("start")
    def start(self, **options) -> None:
        """ Start the interpreter globals dict with all options on setup. """
        self.console_vars = {"options": options}

    @on("debug_vars")
    def set_debug(self, *, components=(), **dvars) -> None:
        """ Add debug variables such as the components (keyed by module path) to the interpreter globals.
            Sort the entire list at the end. Make a new globals dict; it will remember the new insertion order. """
        all_items = [*dvars.items(), *self.console_vars.items()]
        all_items += [("_".join(str_prefix(type(c).__module__, ".base").rsplit(".", 2)[-2:]), c) for c in components]
        self.console_vars = dict(sorted(all_items))

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
            sys.displayhook = lambda v: self.console.write(f"{v!r}\n")
            self.send()
        self.dialog.show()

    def send(self, text_in:str="") -> None:
        """ When the dialog sends a new line of input, push to the console. """
        more = 0
        try:
            self.console.write(text_in)
            more = self.console.push(text_in)
        except KeyboardInterrupt:
            self.console.write("\nKeyboardInterrupt\n")
            self.console.resetbuffer()
        self.console.write("... " if more else ">>> ")

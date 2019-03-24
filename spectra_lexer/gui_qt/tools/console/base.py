from .console_dialog import ConsoleDialog
from .interpreter import InterpreterConsole
from spectra_lexer import Component


class ConsoleTool(Component):
    """ Component for interactive engine and system interpreter operations. """

    console_menu = Resource("menu", "Tools:Open Console...", ["console_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    console: InterpreterConsole = None  # Main interpreter console, run on a different thread.
    dialog: ConsoleDialog = None        # Currently active interpreter dialog window.
    console_vars: dict = {}             # Variables to load on interpreter startup.

    @on("start")
    def start(self, **options) -> None:
        """ Add all global options to the interpreter on setup. """
        self.console_vars = options

    @on("console_dialog_open")
    def open(self) -> None:
        """ Start the interpreter console with the current vars dict and show the initial generated text in a dialog.
            If it already is started, just show the dialog again with the current text contents. """
        if self.console is None:
            self.console = InterpreterConsole(self.console_vars)
        if self.dialog is None:
            self.dialog = ConsoleDialog(self.window, self.input_line)
        self.dialog.show()
        self.dialog.set_text(self.console.send())

    def input_line(self, text:str) -> None:
        """ When the dialog sends a new line of input, give to the console and return its output to the dialog. """
        output = self.console.send(text)
        self.dialog.set_text(output)

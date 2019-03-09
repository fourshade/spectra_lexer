from typing import Optional

from .interpreter import InterpreterConsole
from spectra_lexer import Component


class ConsoleTool(Component):
    """ Component for interactive engine and system interpreter operations. """

    console_menu = Option("menu", "Tools:Open Console...", ["console_open"])

    console: InterpreterConsole = None  # Main interpreter console, run on a different thread.
    console_vars: dict = None           # Variables to load on interpreter startup.

    @on("setup")
    def new_options(self, **options) -> None:
        """ Add all global options to the interpreter on setup. """
        self.console_vars = options

    @pipe("console_open", "new_interactive_text", keyboard=True, scroll_to="bottom")
    def open(self) -> str:
        """ Start the interpreter console with the current vars dict and return the initial generated text.
            If it already is started, just show the current text contents again. Enable keyboard input as well. """
        if self.console is None:
            self.console = InterpreterConsole(self.console_vars)
        self.engine_call("new_status", "Python Console")
        return self.console.send()

    @pipe("text_keyboard_input", "new_interactive_text", keyboard=True, scroll_to="bottom")
    def system_command(self, text:str) -> Optional[str]:
        """ Send text to the console if it's started, else do nothing. """
        if self.console is not None:
            return self.console.send(text)

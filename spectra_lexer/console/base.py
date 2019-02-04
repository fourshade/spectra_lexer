from typing import Optional

from spectra_lexer import Component, on, pipe
from spectra_lexer.console.interpreter import InterpreterConsole


class SpectraConsole(Component):
    """ Component for interactive engine and system interpreter operations. """

    ROLE = "console"

    console: InterpreterConsole = None  # Main interpreter console, run on a different thread.
    console_vars: dict = None           # Variables to load on interpreter startup.

    @on("start")
    def start(self, console_vars:dict=None, **opts) -> None:
        """ Use the vars dict on interpreter start if given, otherwise just use the defaults. """
        self.console_vars = console_vars or {}

    @pipe("console_open", "new_console_text", scroll_to="bottom")
    def open(self) -> str:
        """ Start the interpreter console with the current vars dict and return the initial generated text.
            If it already is started, just show the current text contents again. """
        if self.console is None:
            self.console = InterpreterConsole(self.console_vars)
        self.engine_call("new_status", "Python Console")
        return self.console.send()

    @pipe("console_input", "new_console_text", scroll_to="bottom")
    def system_command(self, text:str) -> Optional[str]:
        """ Send text to the console if it's started, else do nothing. """
        if self.console is not None:
            return self.console.send(text)

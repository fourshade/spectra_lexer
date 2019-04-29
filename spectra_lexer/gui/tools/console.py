from functools import partial
from typing import Callable

from spectra_lexer.core import Component


class ConsoleTool(Component):
    """ Abstract GUI component for system interpreter I/O. """

    m_console = resource("menu:Debug:Open Console...", ["console_tool_open"])

    @on("console_tool_open")
    def open(self) -> None:
        """ Open the dialog and start the interpreter by sending it a blank line. """
        input_callback = partial(self.engine_call, "console_input")
        self.open_dialog(input_callback)
        input_callback("")

    def open_dialog(self, input_callback:Callable) -> None:
        raise NotImplementedError

    @on("new_console_output")
    def output(self, text:str) -> None:
        """ Subclasses must handle console output here. If they don't, it just disappears. """

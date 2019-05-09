from functools import partial

from .base import GUITool


class ConsoleTool(GUITool):
    """ Abstract GUI component for system interpreter I/O. """

    m_console = resource("menu:Debug:Open Console...", ["console_tool_open"])

    @on("console_tool_open")
    def open(self) -> None:
        """ Open a new dialog and start the interpreter. """
        input_callback = partial(self.engine_call, "console_input")
        self.open_dialog(input_callback)
        self.engine_call("console_start", interactive=True)

    @on("new_console_output")
    def output(self, text:str) -> None:
        """ If a dialog exists, send all console output text there. """
        if self._dialog is not None:
            self.send_to_dialog(self._dialog, text)

    def send_to_dialog(self, dialog, text:str) -> None:
        """ Subclasses must handle console output here. """
        raise NotImplementedError

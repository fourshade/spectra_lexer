import sys
import traceback

from spectra_lexer import fork, on, pipe, SpectraComponent

from spectra_lexer.system.console import InterpreterConsole

# Map of commands that can be sent from text entry.
_COMMAND_MAP = {"/console": "system_console_start"}


class SystemModule(SpectraComponent):
    """ Module for low-level system interpreter operations such as exception handling and debugging. """

    console = None

    @on("new_status")
    def print_status(self, msg:str) -> None:
        """ Default system response to status messages is to print them to console. """
        print(msg)

    @fork("handle_exception", "new_output_text")
    def display_exception(self, e:Exception) -> str:
        """ The stack trace for unhandled exceptions are piped to every main display surface, including the main
            GUI window and the console. To avoid crashing Plover, exceptions are marked as handled after display. """
        tb_lines = traceback.TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        return "".join(tb_text)

    @pipe("new_text_entry", "new_output_text", scroll_to="bottom")
    def system_command(self, text:str) -> str:
        """ Special system features may be enabled on text entry.
            If none match, send it to the console and output any new generated text. """
        special = _COMMAND_MAP.get(text)
        if special:
            self.engine_send(special)
        else:
            if self.console is not None:
                return self.console.run_command(text)

    @pipe("system_console_start", "new_output_text", scroll_to="bottom")
    def console_start(self) -> str:
        """ Start the interpreter console with the engine state and return the initial generated text. """
        if self.console is None:
            self.console = InterpreterConsole(locals={"engine": self.engine_call.__self__})
            return self.console.read()

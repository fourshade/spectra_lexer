from traceback import TracebackException

from .interpreter import Console, ConsoleTypes
from .tools import WrappedCommand, xhelp
from spectra_lexer.core import Component


class ConsoleManager(Component):
    """ Component for engine and system interpreter operations.
        Handles the most fundamental operations of the system, including status and exceptions. """

    debug_vars = resource("debug", {})  # Contains all application-level global variables

    _console: Console = None  # Main interpreter console.

    @on("console_start")
    def console_start(self, *, interactive:bool=True) -> str:
        """ (Re)start the console with a copy of the current debug dict. """
        d_vars = dict(self.debug_vars)
        # Start a console locals namespace with every engine command, wrapped in the original function info.
        locals_ns = {k: WrappedCommand(f_list, self.engine_call) for k, f_list in d_vars.get("commands", {}).items()}
        # Start the interpreter console with the output callback and some extra tools.
        self._console = ConsoleTypes[interactive](locals_ns, app=d_vars, help=xhelp())
        return self.console_in()

    @on("console_input")
    def console_in(self, text_in:str=None) -> str:
        """ Process a new string of input text and send the output to the engine. """
        text_out = self._console.run(text_in)
        self.engine_call("new_console_output", text_out)
        return text_out

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console by default. """
        print(f"SPECTRA: {msg}")

    @on("exception")
    def exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to the console, if possible. Return the exception if unsuccessful.
            Send the traceback text to the engine in case GUI components want to display it. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            self.engine_call("new_traceback", tb_text)
            print(tb_text)
        except Exception as e:
            return e

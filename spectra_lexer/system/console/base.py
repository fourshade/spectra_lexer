import sys
from functools import partial, update_wrapper
from traceback import TracebackException

from .interpreter import SpectraConsole
from .tools import ConsoleTools
from spectra_lexer.core import Component


class ConsoleManager(Component):
    """ Component for engine and system interpreter operations.
        Handles the most fundamental operations of the system, including status and exceptions. """

    debug_vars = resource("debug", {})  # Variables to load on interpreter startup as globals.

    _console: SpectraConsole = None  # Main interpreter console.

    @on("console_input")
    def send(self, text:str) -> None:
        """ Send a new string of text to the interpreter console. If not started, start it with the debug dict. """
        if self._console is None:
            # The console locals must be a normal dict. A defaultdict will cause lots of problems.
            d = dict(self.debug_vars)
            # Write the startup sequence manually, before adding the commands.
            callback = partial(self.engine_call, "new_console_output")
            callback(f"Python {sys.version}\n"
                     f"SPECTRA DEBUG CONSOLE - Current global objects:\n{[*d]}\n"
                     f"Type 'list(commands)' to see a list of engine commands.\n")
            # Add every engine command to the top-level locals, wrapped in the original function info.
            for k, f in d.get("commands", {}).items():
                d[k] = update_wrapper(partial(self.engine_call, k), f)
            # Add everything public from the tools class and start the interpreter.
            d.update({k: v for k, v in vars(ConsoleTools).items() if not k.startswith("_")})
            self._console = SpectraConsole(d, callback)
        self._console.send(text)

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console by default. """
        print(f"SPECTRA: {msg}")

    @on("exception")
    def exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to stderr, if possible. Return the exception if unsuccessful. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            sys.stderr.write(tb_text)
        except Exception as e:
            return e

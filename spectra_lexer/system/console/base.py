from code import InteractiveInterpreter
import sys
from traceback import TracebackException

from ..app import SYSApp
from ..control import SYSControl
from .interpreter import ConsoleIO
from .tools import WrappedCommand, xhelp
from spectra_lexer.core import Command, CommandClass, Component, COREEngine, Signal
from spectra_lexer.types.importer import AutoImporter

# Decorator for a string command available as a function in the console. Must return or save a useful value.
ConsoleCommand = CommandClass(console_key="")


class SYSConsole:

    @Command
    def open(self, **kwargs) -> str:
        """ Open the console with all engine commands, each wrapped in the original function info. """
        raise NotImplementedError

    @Command
    def input(self, text_in:str) -> str:
        """ Process a string of input text and send any resulting output to the engine. """
        raise NotImplementedError

    class Output:
        @Signal
        def on_console_output(self, text:str) -> None:
            raise NotImplementedError


class ConsoleManager(Component, SYSConsole, SYSControl,
                     SYSApp.Components,
                     COREEngine.Exception):
    """ Component for engine and system interpreter operations.
        Handles the most fundamental operations of the system, including status and exceptions. """

    _console: ConsoleIO = None  # Main interpreter console IO interface.

    def open(self, **kwargs) -> str:
        """ Use a namespace dict that automatically imports top-level modules for convenience. """
        wrapped_commands = {k: WrappedCommand(k, v, self.engine_call) for k, v in ConsoleCommand.items()}
        locals_ns = AutoImporter.make_namespace(wrapped_commands, __app__=tuple(self.components), help=xhelp())
        self._console = ConsoleIO(InteractiveInterpreter(locals_ns), **kwargs)
        return self._send_output()

    def input(self, text_in:str) -> str:
        self._console.input(text_in)
        return self._send_output()

    def _send_output(self) -> str:
        """ Read any available console output and send it to the engine. """
        text_out = self._console.output()
        self.engine_call(self.Output, text_out)
        return text_out

    def status(self, message:str) -> None:
        """ Display status messages in the console by default. """
        print(f"SPECTRA: {message}")

    def exit(self) -> None:
        sys.exit()

    def on_engine_exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to the console, if possible. Return the exception if unsuccessful. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            print(tb_text)
        except Exception as e:
            return e

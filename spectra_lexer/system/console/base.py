from traceback import TracebackException
from typing import Callable, Iterable, Iterator

from ..base import SYS
from .interpreter import ConsoleIO
from .tools import HelpWrapper, xhelp
from spectra_lexer.core import Command
from spectra_lexer.types.importer import AutoImporter


class ConsoleCommand(Command):
    """ Decorator for a string command available as a function in the console. """

    _COMMANDS = {}  # Dict of all commands directly available in the console.

    def bind(self, *args) -> Iterable[Callable]:
        """ Only one component may answer each function, and it should return or save a useful value. """
        for meth in super().bind(*args):
            self._COMMANDS[self.__name__] = HelpWrapper(meth, self)
            yield meth

    @classmethod
    def make_namespace(cls):
        """ Use a namespace dict that automatically imports top-level modules for convenience. """
        return AutoImporter.make_namespace(cls._COMMANDS, help=xhelp())


class ConsoleManager(SYS):
    """ Component for engine and system interpreter operations.
        Handles the most fundamental operations of the system, including status and exceptions. """

    _console: ConsoleIO = None  # Main interpreter console IO interface.

    def SYSConsoleOpen(self, *args, **kwargs) -> str:
        self._new_console(*args, **kwargs)
        return self._console.output()

    def _new_console(self, *args, **kwargs) -> None:
        """ Make a new namespace and console. If positional args are given, they add entries to the namespace. """
        locals_ns = ConsoleCommand.make_namespace()
        if args:
            locals_ns.update(*args)
        self._console = ConsoleIO(locals_ns, **kwargs)

    def SYSConsoleInput(self, text_in:str) -> str:
        self._console.input(text_in)
        return self._console.output()

    def SYSConsoleBatch(self, *commands:str) -> int:
        self._new_console(interactive=False)
        return self._loop(self._console.run_batch(*commands))

    def SYSConsoleRepl(self, input_cb:Callable[[], str]=input) -> int:
        self._new_console(interactive=True)
        return self._loop(self._console.run_repl(input_cb))

    def _loop(self, iterator:Iterator[str]) -> int:
        """ Run an iterator operation and print all text to stdout. """
        for text_out in iterator:
            print(text_out, end='')
        return 0

    def SYSStatus(self, status:str) -> None:
        """ Display status messages on stdout by default. """
        print(f"SPECTRA: {status}")

    def Exception(self, *exc_args) -> bool:
        """ Print an exception traceback to stdout, if possible.
            Also send the traceback text to any other component that wants it. """
        tb_text = ExceptionFormatter(*exc_args).format()
        try:
            print(tb_text)
        except Exception as e:
            # stdout might be locked or redirected. We're probably screwed, but there may be other handlers.
            tb_text += f"\nFAILED TO WRITE STDOUT!\n{ExceptionFormatter.from_exception(e).format()}"
        self.SYSTraceback(tb_text)
        return True


class ExceptionFormatter(TracebackException):

    def format(self, **kwargs) -> str:
        """ Perform custom formatting of a traceback and return a string. """
        lines = super().format(**kwargs)
        return "".join(lines)

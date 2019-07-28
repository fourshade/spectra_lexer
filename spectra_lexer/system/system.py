from itertools import islice
import sys
from traceback import TracebackException
from typing import List

from .base import SYS
from .console import SystemConsole
from .io import PathIO
from .log import StreamLogger
from spectra_lexer.core import CmdlineOption


class SystemManager(SYS):
    """ Component for handling the command line, console, files, and logging engine status and exceptions. """

    log_file: str = CmdlineOption("log-file", default="~/status.log",
                                  desc="Text file to log status and exceptions.")

    _io: PathIO            # Reads, writes, and converts path strings.
    _logger: StreamLogger  # Logs system events to standard streams and/or files.
    _components: list      # Contains every component definition in the application.
    _console: SystemConsole = None

    def __init__(self):
        self._io = PathIO(**self.get_root_paths())
        self._logger = StreamLogger(sys.stdout)
        self._components = [self]

    def Load(self) -> None:
        log_path = self._io.to_path(self.log_file)
        self._logger.add_path(log_path)

    def Debug(self, components:list) -> None:
        self._components = components

    def SYSConsoleOpen(self, *, interactive:bool=True, **kwargs) -> None:
        kwargs["__app__"] = self._components
        self._console = SystemConsole(self.SYSConsoleOutput, interactive, self.CONSOLE_COMMANDS, **kwargs)

    def SYSConsoleInput(self, text_in:str) -> None:
        if self._console is not None:
            self._console.run(text_in)

    def SYSFileLoad(self, *patterns:str, **kwargs) -> List[bytes]:
        return [*self._io.read(*patterns, **kwargs)]

    def SYSFileSave(self, data:bytes, filename:str) -> None:
        self._io.write(data, filename)

    def SYSStatus(self, status:str) -> None:
        """ Log and print status messages to stdout by default. """
        self._logger(status)

    def HandleException(self, exc:Exception, max_lines:int=50) -> bool:
        """ Log and print an exception traceback to stdout, if possible.
            Also send the traceback text to any other component that wants it. """
        tb = TracebackException.from_exception(exc)
        tb_text = "".join(islice(tb.format(), max_lines))
        self._logger(f'EXCEPTION\n{tb_text}')
        self.SYSTraceback(tb_text)
        return True

    @classmethod
    def get_root_paths(cls) -> dict:
        """ The name of this class's root package is used as a default path for built-in assets and user files. """
        root_package = cls.__module__.split(".", 1)[0]
        return {"asset_path": root_package,  # Root directory for application assets.
                "user_path":  root_package}  # Root directory for user data files.

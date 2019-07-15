import sys
from typing import List

from .base import CmdlineOption, SYS
from .cmdline import CmdlineParser
from .console import SystemConsole
from .io import PathIO
from .log import SystemLogger


class SystemManager(SYS):
    """ Component for handling the command line, console, files, and logging engine status and exceptions. """

    log_file: str = CmdlineOption("log-file", default="~/status.log",
                                  desc="Text file to log status and exceptions.")

    _io: PathIO = None              # Reads, writes, and converts path strings.
    _logger: SystemLogger = None    # Logs system events to standard streams and/or files.
    _console: SystemConsole = None

    def __init__(self):
        self._io = PathIO(**self.get_root_paths())
        self._logger = SystemLogger()
        self._logger.add_stream(sys.stdout)

    def Load(self) -> None:
        """ Create the parser and add all possible command line options from each component that has some.
            Parse arguments from the app and update all command line options on existing components. """
        parser = CmdlineParser(*self.CMDLINE_INFO)
        self.CMDLINE_INFO = [*parser.parse().items()]
        log_path = self._io.to_path(self.log_file)
        self._logger.add_file(log_path)

    def SYSConsoleOpen(self, *, interactive:bool=True, **kwargs) -> None:
        kwargs["__app__"] = self.ALL_COMPONENTS
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
        self._logger.info(status)

    def HandleException(self, exc:Exception) -> bool:
        """ Log and print an exception traceback to stdout, if possible.
            Also send the traceback text to any other component that wants it. """
        tb_text = self._logger.exception(exc)
        self.SYSTraceback(tb_text)
        return True

    @classmethod
    def get_root_paths(cls) -> dict:
        """ The name of this class's root package is used as a default path for built-in assets and user files. """
        root_package = cls.__module__.split(".", 1)[0]
        return {"asset_path": root_package,  # Root directory for application assets.
                "user_path":  root_package}  # Root directory for user data files.

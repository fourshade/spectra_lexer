import sys
from traceback import TracebackException
from typing import List

from .base import CORE
from .cmdline import CmdlineOption
from .console import HelpWrapper, SystemConsole, xhelp
from .io import PathIO
from .log import StreamLogger


class SpectraCore(CORE):
    """ Component for handling the command line, console, files, and logging engine status and exceptions. """

    log_file: str = CmdlineOption("log-file", default="~/status.log",
                                  desc="Text file to log status and exceptions.")

    _io: PathIO            # Reads, writes, and converts path strings.
    _logger: StreamLogger  # Logs system events to standard streams and/or files.
    _debug_dict: dict = {"NO DATA": "Debug info is missing."}
    _console: SystemConsole = None

    def __init__(self):
        self._io = PathIO(**self.get_root_paths())
        self._logger = StreamLogger(sys.stdout)

    def Load(self) -> None:
        log_path = self._io.to_path(self.log_file)
        self._logger.add_path(log_path)

    def COREDebug(self, debug_dict:dict) -> None:
        self._debug_dict = debug_dict.copy()

    def COREConsoleOpen(self, *, interactive:bool=True) -> None:
        commands = {cmd.__name__: HelpWrapper(cmd) for cmd in self.CONSOLE_COMMANDS}
        self._debug_dict.update(commands, help=xhelp())
        self._console = SystemConsole(self.COREConsoleOutput, interactive, self._debug_dict)

    def COREConsoleInput(self, text_in:str) -> None:
        if self._console is not None:
            self._console.run(text_in)

    def COREFileLoad(self, *patterns:str, **kwargs) -> List[bytes]:
        return [*self._io.read(*patterns, **kwargs)]

    def COREFileSave(self, data:bytes, filename:str) -> None:
        self._io.write(data, filename)

    def COREStatus(self, status:str) -> None:
        """ Log and print status messages to stdout by default. """
        self._logger(status)

    def COREException(self, exc:Exception, max_frames:int=10) -> bool:
        """ Log and print an exception traceback to stdout, if possible, and save the exception for introspection. """
        tb = TracebackException.from_exception(exc, limit=max_frames)
        tb_text = "".join(tb.format())
        self._logger(f'EXCEPTION\n{tb_text}')
        self._debug_dict["last_exception"] = exc
        return True

    @classmethod
    def get_root_paths(cls) -> dict:
        """ The name of this class's root package is used as a default path for built-in assets and user files. """
        root_package = cls.__module__.split(".", 1)[0]
        return {"asset_path": root_package,  # Root directory for application assets.
                "user_path":  root_package}  # Root directory for user data files.

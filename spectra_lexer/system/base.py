import sys
from traceback import TracebackException
from typing import Callable, List

from .console import SystemConsole
from .debug import DebugDict
from .io import PathIO
from .log import StreamLogger

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class SystemLayer:
    """ Component for handling the command line, console, files, and logging status and exceptions. """

    _io: PathIO             # Performs all necessary filesystem and asset I/O.
    _logger: StreamLogger   # Logs system events to standard streams and/or files.
    _debug_vars: DebugDict  # Tracks major app components for console debugging.

    def __init__(self, asset_path:str=ROOT_PACKAGE, user_path:str=ROOT_PACKAGE):
        self._io = PathIO(asset_path, user_path)
        self._logger = StreamLogger(sys.stdout)
        self._debug_vars = DebugDict()

    def read_all(self, *patterns:str, **kwargs) -> List[bytes]:
        """ Read bytes objects from one or more expanded file path strings. """
        return [*self._io.read(*patterns, **kwargs)]

    def read(self, *patterns, **kwargs) -> bytes:
        """ Read only the first file out of the given patterns (if any). """
        data_list = self.read_all(*patterns, **kwargs)
        return data_list[0] if data_list else b""

    def write(self, data:bytes, filename:str) -> None:
        """ Write a bytes object to a file path. """
        self._io.write(data, filename)

    def file_exists(self, filename:str) -> bool:
        return self._io.exists(filename)

    def log(self, msg:str) -> None:
        """ Log a message to every registered file and stream. """
        self._logger(msg)

    def log_exception(self, exc:Exception, max_frames:int=10) -> str:
        """ Handle a top-level exception by logging and/or displaying it.
            Log and print an exception traceback to stdout, if possible, and save the exception for introspection. """
        tb = TracebackException.from_exception(exc, limit=max_frames)
        tb_text = "".join(tb.format())
        self.log(f'EXCEPTION\n{tb_text}')
        self._debug_vars["last_exception"] = exc
        return tb_text

    def log_to(self, filename:str) -> None:
        """ Start logging to the specified file (in addition to any previous ones). """
        log_path = self._io.expand(filename)
        self._logger.add_path(log_path)

    def __setitem__(self, key:str, obj:object) -> None:
        """ Add an object to the debug namespace dict as a component. """
        self._debug_vars.add_component(key, obj)

    def debug_ns(self) -> dict:
        """ Return a public shallow copy of the debug namespace dict. """
        return self._debug_vars.copy()

    def open_console(self, write_to:Callable[[str], None]=None) -> Callable[[str], None]:
        """ Open a console with the debug namespace dict and return it.
            The console object is called with text input and forwards output to stdout and/or <write_to>. """
        return SystemConsole(self._debug_vars, write_to)

    def repl(self, *args, input_fn=input) -> None:
        """ Run an interactive read-eval-print loop in a new console. Only a SystemExit can break out of this. """
        console = self.open_console(*args)
        while True:
            console(input_fn())

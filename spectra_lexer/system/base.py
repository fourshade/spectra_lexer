import pkgutil
import sys
from traceback import TracebackException
from typing import Callable, List

from .console import SystemConsole
from .debug import DebugTree
from .io import PathIO
from .log import StreamLogger

# The name of this module's root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]


class AutoImporter(dict):
    """ Interpreter namespace dict that functions as a copy of __builtins__ with extra features.
        It automatically tries to import missing modules any time code would otherwise throw a NameError. """

    __slots__ = ()

    @classmethod
    def namespace(cls, *args, **builtins):
        """ Auto-import tends to pollute namespaces with tons of garbage. We don't need that at the top level.
            The actual auto-import dict is hidden as __builtins__, and is tried only after the main dict fails. """
        # The constructor will copy the real global builtins dict; it won't be corrupted.
        return dict(*args, __builtins__=cls(__builtins__, **builtins))

    def __missing__(self, k:str):
        """ Try to import missing modules before raising a KeyError (which becomes a NameError).
            If successful, attempt to import submodules recursively. """
        try:
            module = self[k] = __import__(k, self, locals(), [])
        except Exception:
            raise KeyError(k)
        try:
            for finder, name, ispkg in pkgutil.walk_packages(module.__path__, f'{k}.'):
                __import__(name, self, locals(), [])
        except Exception:
            pass
        return module


class SystemLayer:
    """ Component for handling the command line, console, files, and logging status and exceptions. """

    _io: PathIO             # Performs all necessary filesystem and asset I/O.
    _logger: StreamLogger   # Logs system events to standard streams and/or files.
    _components: dict       # Tracks major app components for console and debugging use.

    def __init__(self, asset_path:str=ROOT_PACKAGE, user_path:str=ROOT_PACKAGE):
        self._io = PathIO(asset_path, user_path)
        self._logger = StreamLogger(sys.stdout)
        self._components = {}

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
        self._components["last_exception"] = exc
        return tb_text

    def log_to(self, filename:str) -> None:
        """ Start logging to the specified file (in addition to any previous ones). """
        log_path = self._io.expand(filename)
        self._logger.add_path(log_path)

    def __setitem__(self, key:str, obj:object) -> None:
        """ Add an object to the component dict. """
        self._components[key] = obj

    def debug_tree(self, **kwargs) -> DebugTree:
        """ Make and return a debug tree structure from a copy of our current component dict. """
        return DebugTree(self._components.copy(), AutoImporter.namespace(), **kwargs)

    def open_console(self, **kwargs) -> Callable[[str], None]:
        """ Open a console with the debug components and return it.
            The console object is called with text input and forwards output to stdout and/or <write_to>. """
        return SystemConsole(AutoImporter.namespace(self._components), **kwargs)

    def repl(self, input_fn=input, **kwargs) -> None:
        """ Run an interactive read-eval-print loop in a new console. Only a SystemExit can break out of this. """
        console = self.open_console(**kwargs)
        while True:
            console(input_fn())

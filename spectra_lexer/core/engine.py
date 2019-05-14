from functools import partial
from queue import Queue
from threading import Thread
from typing import Any, Callable, Hashable, Iterable

from .command import AbstractCommand
from spectra_lexer.types.dict import multidict


class Executor(multidict):
    """ Holds engine commands, each associated with a key. Executes *all* callables under that key when called.
        The return value, if any, is the one from the last callable executed in order. """

    def __call__(self, key:Hashable, *args, **kwargs) -> Any:
        """ Run all callables matching a key and return the last result. """
        value = None
        for func in self[key]:
            value = func(*args, **kwargs)
        return value


class ExceptionHandler:

    _depth: int = 0          # Tracks levels of re-entrancy. 0 is the top level.
    _exc_callback: Callable  # Callable to handle exceptions. Should return True if successful.

    def __init__(self, exc_callback:Callable):
        self._exc_callback = exc_callback

    def __enter__(self) -> None:
        self._depth += 1

    def __exit__(self, exc_type:type, exc_value:Exception, exc_traceback) -> bool:
        """ If there's an exception and we're at the top level, try to handle it with the callback. """
        self._depth -= 1
        if exc_type is None or self._depth:
            return False
        return self._exc_callback(exc_type, exc_value, exc_traceback)


class Engine:
    """ Simple single-threaded engine class class for the Spectra program.
        Routes messages and data structures between all constituent components. """

    _executor: Executor             # Holds and executes commands by key.
    _exc_handler: ExceptionHandler  # Context manager to handle exceptions.

    def __init__(self, components:Iterable[object], *, exc_command:Hashable=None):
        """ Bind commands from components and assemble the engine with an executor and/or exception handler. """
        super().__init__()
        self._executor = Executor()
        self._exc_handler = ExceptionHandler(partial(self._handle_exception, exc_command))
        for cmp in components:
            self.connect(cmp)

    def connect(self, cmp:object) -> None:
        """ Bind this component to all engine commands. """
        self._executor.update(AbstractCommand.bind_all(cmp, self))

    def __call__(self, *args, **kwargs) -> Any:
        """ Central method for components to call commands on other components. """
        return self._exec(*args, **kwargs)

    def _exec(self, *args, **kwargs) -> Any:
        """ Run an engine command and handle any exceptions. """
        with self._exc_handler:
            return self._executor(*args, **kwargs)

    def _handle_exception(self, exc_command:Callable, *exc_args) -> bool:
        """ C frameworks may crash if exceptions propagate back to them, so try to handle them here if possible. """
        if exc_command is None:
            return False
        self(exc_command, *exc_args)
        return True


class ThreadedEngine(Engine, Queue):
    """ Engine that services its own, isolated group of components on a separate thread by taking external commands
        from a queue and calling them on its group. Commands *from* its group are also routed to other engines. """

    connections: Iterable[Callable] = ()  # All connected engine queue callbacks.
    start: Callable[[], None]             # Thread start method.

    def __init__(self, components:Iterable[object], **kwargs):
        """ Make a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        super().__init__(components, **kwargs)
        self.start = Thread(target=self._loop, name=f"THREAD: {components}", daemon=True).start

    def __call__(self, *args, **kwargs) -> Any:
        """ Echo new commands to all connected engines before executing them ourselves. """
        cmd = args, kwargs
        for callback in self.connections:
            callback(cmd)
        return self._exec(*args, **kwargs)

    def call_ext(self, cmd:tuple) -> None:
        """ Execute a command from another engine. These calls cannot return a value to that engine. """
        args, kwargs = cmd
        self._exec(*args, **kwargs)

    def _loop(self) -> None:
        """ Execute commands in our queue. They have been sent by other threads, so we do not need to echo them. """
        while True:
            self.call_ext(self.get())


class ThreadedEngineGroup(ThreadedEngine):
    """ A composite threaded engine consisting of multiple component groups. """

    def __init__(self, groups:Iterable[Iterable[object]], passthrough:Callable=None, **kwargs):
        """ The first component group is designated the "main group", and is directly connected to this engine.
            Each further group is a "worker group", which gets its own thread and child engine. """
        main_group, *worker_groups = groups
        super().__init__(main_group, **kwargs)
        child_engines = [ThreadedEngine(group, **kwargs) for group in worker_groups]
        if passthrough is not None:
            # Some components may need to run functions on the main thread (typically the thread calling *this* method).
            # These components must be included in the main group. A passthrough function may then be given that
            # notifies the main thread when it needs to run a command on this group. """
            self.call_ext = passthrough(self.call_ext)
        # Each engine must connect to every other engine in order for all commands to be routed correctly.
        engines = [self, *child_engines]
        for e in engines:
            e.connections = [other.put for other in engines if other is not e]
            e.start()

from queue import Queue
from threading import Thread
from typing import Any, Callable, Hashable, Iterable, Tuple

from .component import AbstractMod, Component, Signal
from spectra_lexer.types.dict import multidict


class Executor:
    """ Holds engine commands, each associated with a key. Executes *all* callables under that key when called.
        The return value, if any, is the one from the last callable executed in order. """

    _commands: multidict  # Holds command keys mapped to lists of callable commands.

    def __init__(self, commands:Iterable[Tuple[Hashable, Callable]]=()):
        super().__init__()
        self._commands = multidict(commands)

    def __call__(self, key:Hashable, *args, **kwargs) -> Any:
        """ Run all callables matching a key and return the last result. """
        value = None
        for func in self._commands[key]:
            value = func(*args, **kwargs)
        return value


class COREEngine:

    class Exception:
        @Signal
        def on_engine_exception(self, exc_value:Exception) -> None:
            """ Handle an exception, if possible. """
            raise NotImplementedError


class Engine(COREEngine):
    """ Simple single-threaded engine class class for the Spectra program.
        Routes messages and data structures between all constituent components. """

    _executor: Executor  # Holds and executes commands by key.

    def __init__(self, components:Iterable[Component]):
        """ Bind commands from an iterable of components and assemble the engine with an executor. """
        super().__init__()
        self._executor = Executor([cmd for cmp in components for cmd in self.connect(cmp)])

    def connect(self, cmp:Component) -> Iterable[Tuple[Hashable, Callable]]:
        """ Connect this component to the engine callback and bind to all engine commands. """
        cmp.engine_connect(self)
        return AbstractMod.bind_all(cmp)

    def __call__(self, *args, **kwargs) -> Any:
        """ Central method for components to call commands on other components. """
        return self._exec(*args, **kwargs)

    def _exec(self, *args, **kwargs) -> Any:
        """ Run an engine command and handle any exceptions with a signal to components.
            C frameworks may crash if exceptions propagate back to them, so try to handle them here if possible. """
        try:
            return self._executor(*args, **kwargs)
        except Exception as exc_value:
            # If the last call was handling an exception of the same type, re-raise to halt recursion.
            if type(exc_value) in set(map(type, args)):
                raise
            self(self.Exception, exc_value)


class ThreadedEngine(Engine, Queue):
    """ Engine that services its own, isolated group of components on a separate thread by taking external commands
        from a queue and calling them on its group. Commands *from* its group are also routed to other engines. """

    connections: Iterable[Callable] = ()  # All connected engine queue callbacks.
    start: Callable[[], None]             # Thread start method.

    def __init__(self, components:Iterable[Component]):
        """ Make a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        super().__init__(components)
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

    @classmethod
    def group(cls, components:Iterable[Iterable[Component]], passthrough:Callable=None) -> Engine:
        """ Create a composite threaded engine consisting of multiple component groups.
            The first level of items in <components> determines the number of sub-engines/threads.
            The first component group is designated the "main group", and its engine the "main engine",
            which is returned as the direct callable output of this method. """
        engines = list(map(cls, components))
        main_engine = engines[0]
        if passthrough is not None:
            # Some components may need to run functions on the main thread (typically the thread calling *this* method).
            # These components must be included in the main group. A passthrough function may then be given that
            # notifies the main thread when it needs to run a command on this group. """
            main_engine.call_ext = passthrough(main_engine.call_ext)
        # Each engine must connect to every other engine in order for all commands to be routed correctly.
        for self in engines:
            self.connections = [e.put for e in engines if e is not self]
            self.start()
        return main_engine

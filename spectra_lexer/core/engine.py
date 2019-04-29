from queue import Queue
from threading import Thread
from typing import Any, Callable, Iterable, Tuple


class Engine:
    """ Base engine class for the Spectra program. """

    _call: Callable[[str, tuple, dict], Any] = None  # Runtime that handles commands and exceptions.

    def set_runtime(self, runtime:Callable[[str, tuple, dict], Any]):
        self._call = runtime

    def call(self, key:str, *args, **kwargs) -> Any:
        """ Call a command with varargs converted to basic positional arguments. """
        return self._call(key, args, kwargs)


class ConnectedEngine(Engine):
    """ Engine that may connect to and call other engines. Any call to an external engine can never return a value. """

    _connections: Iterable = ()  # Iterable of connected engine objects.

    def call(self, key:str, *args, **kwargs) -> Any:
        """ Echo new commands to connected engines before calling them ourselves. """
        cmd = key, args, kwargs
        for engine in self._connections:
            engine.receive(cmd)
        return self._call(*cmd)

    def receive(self, cmd:Tuple[str, tuple, dict]) -> None:
        raise NotImplementedError


class ThreadedEngine(ConnectedEngine):
    """ Engine that services its own, isolated group of components on a separate thread by taking external commands
        from a queue and calling everything it can within its own internal group. """

    _queue: Queue = None  # Thread-safe queue to hold command tuples from other threads.

    def start(self, parent:ConnectedEngine) -> None:
        """ Start a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        self._queue = Queue()
        self._connections = [parent]
        Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        """ Call commands in our queue. They have been sent by other threads, so we do not need to echo them. """
        while True:
            self._call(*self._queue.get())

    def receive(self, cmd:Tuple[str, tuple, dict]) -> None:
        """ Add a command to this engine's queue. Called by the main thread. """
        self._queue.put(cmd)


class MainEngine(ConnectedEngine):
    """ Main engine for components grouped into threads. Components within a single group can communicate freely;
        external communication is only allowed between the main engine and a child, and is strictly unidirectional. """

    def receive(self, cmd:Tuple[str, tuple, dict]) -> None:
        """ Call an outside command in tuple form on this engine. """
        self._call(*cmd)

    def set_passthrough(self, passthrough:Callable) -> None:
        """ Since this engine runs on the main thread, a passthrough function may be given
            that notifies the main thread when it needs to receive a command. """
        self.receive = passthrough(self.receive)

    def connect(self, engine:ThreadedEngine) -> None:
        """ Connect a new child engine and start it. These can never be disconnected. """
        self._connections = [*self._connections, engine]
        engine.start(self)

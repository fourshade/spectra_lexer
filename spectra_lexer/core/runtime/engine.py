from queue import Queue
from threading import Thread
from typing import Any, Callable, Iterable, Tuple


class Engine:
    """ Abstract base engine class for the Spectra program. """

    _call: Callable[[tuple], Any]  # Execution unit that handles commands and exceptions.

    def __init__(self, executor:Callable[[tuple], Any]):
        self._call = executor

    def call(self, *args, **kwargs) -> Any:
        raise NotImplementedError


class SimpleEngine(Engine):
    """ Single-threaded engine class for the Spectra program. Calls are directed straight to the executor. """

    def __init__(self, *args):
        super().__init__(*args)
        self.call = self._call


class ConnectedEngine(Engine):
    """ Engine that may connect to and call other engines. Any call to an external engine can never return a value. """

    _connected_engines: list  # List of connected engine objects.

    def __init__(self, *args):
        super().__init__(*args)
        self._connected_engines = []

    def call(self, *args, **kwargs) -> Any:
        """ Echo new commands to connected engines before calling them ourselves. """
        cmd = args, kwargs
        for engine in self._connected_engines:
            engine.receive(cmd)
        return self._call(*args, **kwargs)

    def receive(self, cmd:Tuple[tuple, dict]) -> None:
        raise NotImplementedError

    def _unpack_call(self, cmd:Tuple[tuple, dict]) -> None:
        args, kwargs = cmd
        self._call(*args, **kwargs)


class ThreadedEngine(ConnectedEngine):
    """ Engine that services its own, isolated group of components on a separate thread by taking external commands
        from a queue and calling everything it can within its own internal group. """

    _queue: Queue = None  # Thread-safe queue to hold command tuples from other threads.

    def start(self, parent_engine:ConnectedEngine) -> None:
        """ Start a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        self._queue = Queue()
        self._connected_engines = [parent_engine]
        self.receive = self._queue.put
        Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        """ Call commands in our queue. They have been sent by other threads, so we do not need to echo them. """
        while True:
            self._unpack_call(self._queue.get())


class MainEngine(ConnectedEngine):
    """ Main engine for components grouped into threads. Components within a single group can communicate freely;
        external communication is only allowed between the main engine and a child, and is strictly unidirectional. """

    def set_passthrough(self, passthrough:Callable) -> None:
        """ Since this engine runs on the main thread, a passthrough function may be given
            that notifies the main thread when it needs to receive a command. """
        self.receive = passthrough(self._unpack_call)

    def connect(self, child_engine:ThreadedEngine) -> None:
        """ Connect a new child engine and start it. These can never be disconnected. """
        self._connected_engines.append(child_engine)
        child_engine.start(self)

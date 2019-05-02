from collections import defaultdict
from queue import Queue
from threading import Thread
from typing import Callable, Dict, List, Tuple


class Engine:
    """ Base engine class for the Spectra program. Has mappings for every command key to a list of callables.
        Commands and components should not change after initialization. """

    _commands: Dict[str, List[Callable]]  # Dict of command keys, each mapped to a list of callable commands.
    _fatal_exceptions: bool = False       # If True, exceptions are propagated instead of caught.

    def __init__(self):
        self._commands = defaultdict(list)

    def add_command(self, key:str, func:Callable) -> None:
        """ Add commands to the engine by key. Commands cannot be disconnected. """
        self._commands[key].append(func)

    def call(self, key:str, *args, **kwargs):
        """ Call a command as basic positional arguments. """
        return self._call(key, args, kwargs)

    def _call(self, key:str, args:tuple, kwargs:dict):
        """ Run all commands matching a key and return the last result. Handle exceptions that make it back here.
            Qt will crash if exceptions propagate back to it; do not allow this under normal circumstances. """
        try:
            value = None
            if key[-1] == ":":
                # The number of trailing colons indicates broadcast nesting depth.
                full_length = len(key)
                key = key.rstrip(":")
                self._broadcast(key, args, kwargs, full_length - len(key))
            for func in self._commands[key]:
                value = func(*args, **kwargs)
            return value
        except Exception as exc_value:
            if self._fatal_exceptions:
                raise
            self.handle_exception(exc_value)

    def _broadcast(self, key:str, args:tuple, kwargs:dict, depth:int=1) -> None:
        """ Broadcast commands require a string dict as the first positional argument and cannot return a value.
            The dict is expanded into a command for each key, called with the value as the first argument. """
        depth -= 1
        d, *args = args
        for k, v in d.items():
            k = f"{key}:{k}"
            v = v, *args
            if depth:
                self._broadcast(k, v, kwargs, depth)
            if self._commands[k]:
                self._call(k, v, kwargs)

    def handle_exception(self, exc_value:Exception) -> bool:
        """ Exception handling is done, like anything else, by calling components.
            Return True if one of them handled the exception. Exceptions in an exception handler are fatal. """
        self._fatal_exceptions = True
        result = self._call("exception", (exc_value,), {})
        self._fatal_exceptions = False
        return bool(result)


class ConnectedEngine(Engine):
    """ Engine that may connect to and call other engines. Any call to an external engine can never return a value. """

    _connections: list  # List of connected engine objects.

    def __init__(self):
        super().__init__()
        self._connections = []

    def call(self, key:str, *args, **kwargs):
        """ Echo new commands to connected engines before calling them ourselves. """
        cmd = key, args, kwargs
        for engine in self._connections:
            engine.receive(cmd)
        return self._call(*cmd)

    def receive(self, cmd:Tuple[str, tuple, dict]) -> None:
        """ Call an outside command in tuple form on this engine. """
        return self._call(*cmd)


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

    def __init__(self, passthrough:Callable[[Callable], Callable]):
        """ Since this engine runs on the main thread, a passthrough function must be given
            that notifies the main thread when it needs to receive a command. """
        super().__init__()
        self.receive = passthrough(self.receive)

    def connect(self, engine:ThreadedEngine) -> None:
        """ Connect a new child engine and start it. These can never be disconnected. """
        self._connections.append(engine)
        engine.start(self)

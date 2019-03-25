from collections import defaultdict
from queue import Queue
from threading import Thread


class Engine:
    """ Base engine class for the Spectra program. Gets its commands by connecting components.
        Has mappings for every command to a list of component+method binding pairs to call.
        Commands and components should not change after initialization. """

    _commands: dict   # Dict of command keys, each mapped to a list of executable commands from components.

    def __init__(self, components:list):
        """ Connect each component by giving it the engine callback and adding the commands it returns to the dict. """
        self._commands = defaultdict(list)
        for c in components:
            for key, cmd in c.engine_connect(self.call):
                self._commands[key].append(cmd)

    def call(self, key, *args, **kwargs):
        """ Run all commands under this key and return the last value. """
        value = None
        for cmp, attr, pipe_to, cmd_kwargs in self._commands[key]:
            value = getattr(cmp, attr)(*args, **kwargs)
            # If there's a follow-up command to run and the output value wasn't None, run it with that value.
            if value is not None and pipe_to is not None:
                # Normal tuples (not subclasses) will be automatically unpacked into the next command.
                next_args = value if type(value) is tuple else (value,)
                self.call(pipe_to, *next_args, **cmd_kwargs)
        return value

    def handle_exception(self, exc_value:Exception) -> bool:
        """ Exception handling is done, like anything else, by calling components. """
        return self.call("exception", exc_value)


class MainEngine(Engine):
    """ Single-threaded main engine class. Tracks the call stack level with an explicit variable. """

    _rlevel: int = 0  # Level of re-entrancy for exceptions, 0 = top of stack.

    def call(self, key, *args, **kwargs):
        """ Run all commands under this key and catch any exceptions that make it to the top level. """
        with self:
            return super().call(key, *args, **kwargs)

    def __enter__(self) -> None:
        """ Re-entrant context manager; used to check exceptions with a custom handler. """
        self._rlevel += 1

    def __exit__(self, exc_type:type, exc_value:Exception, traceback:object) -> bool:
        """ The caller may depend on exceptions, so don't catch them here unless this is the top level. """
        self._rlevel -= 1
        return exc_value is not None and self._rlevel <= 0 and self.handle_exception(exc_value)


class ThreadedEngine(Engine):
    """ Engine that services its own, isolated group of components by taking external commands from a queue and calling
        everything it can within its own internal group. Any call to an external component can never return a value. """

    _parent_send = None  # Callback to send commands to the parent engine.
    _queue: Queue        # Thread-safe queue to hold commands from other threads.

    def __init__(self, components:list, parent_send):
        super().__init__(components)
        self._parent_send = parent_send
        self._queue = Queue()

    def start(self) -> None:
        """ Start a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        """ Call commands in our queue, sending out top-level exceptions. """
        while True:
            try:
                # Commands in our queue have been sent by other threads, so we do not need to echo them.
                key, args, kwargs = self._queue.get()
                super().call(key, *args, **kwargs)
            except Exception as exc_value:
                self.handle_exception(exc_value)

    def call(self, key:str, *args, **kwargs):
        """ Echo every command from our own components to the parent engine before calling it ourselves. """
        self._parent_send((key, args, kwargs))
        return super().call(key, *args, **kwargs)

    def send(self, cmd) -> None:
        """ Add a command to this engine's queue. Called by the main thread. """
        self._queue.put(cmd)

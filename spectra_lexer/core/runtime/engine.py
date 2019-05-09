from queue import Queue
from threading import Thread
from typing import Any, Callable, Sequence


class Engine:
    """ Single-threaded engine class for the Spectra program. Calls are directed straight to the executor. """

    _run_executor: Callable[[tuple], Any]  # Callable that dispatches engine commands.

    def __init__(self, executor:Callable[[tuple], Any]):
        super().__init__()
        self._run_executor = executor

    def call(self, *args, **kwargs) -> Any:
        return self._exec(*args, **kwargs)

    def _exec(self, *args, fatal_exceptions=False, **kwargs) -> Any:
        """ Execute a command and handle exceptions that make it back here.
            Qt will crash if exceptions propagate back to it; do not allow this under normal circumstances. """
        try:
            return self._run_executor(*args, **kwargs)
        except Exception as exc_value:
            # Exception handling is done, like anything else, by calling components.
            # Some apps may lock stderr while running, and a GUI can only print exceptions after setup.
            # Unhandled exceptions in an exception handler are fatal.
            if fatal_exceptions:
                raise
            return self.call("exception", exc_value, fatal_exceptions=True)


class ThreadedEngine(Engine, Queue):
    """ Engine that services its own, isolated group of components on a separate thread by taking external commands
        from a queue and calling them on its group. """

    _connections: Sequence[Callable] = ()  # All connected engine callbacks.

    def connect(self, receiver:Queue) -> None:
        """ Connect another engine to this one. It will receive commands from our components in its queue. """
        self._connections = (*self._connections, receiver.put)

    def set_passthrough(self, passthrough:Callable) -> None:
        """ If an engine needs the main thread, a passthrough function may be given
            that notifies the main thread when it needs to run an external command. """
        self.call_ext = passthrough(self.call_ext)

    def call(self, *args, **kwargs) -> Any:
        """ Echo new commands to connected engines before executing them ourselves. """
        cmd = args, kwargs
        for callback in self._connections:
            callback(cmd)
        return self._exec(*args, **kwargs)

    def call_ext(self, cmd:tuple) -> None:
        """ Execute a command from another engine. These calls cannot return a value to that engine. """
        args, kwargs = cmd
        self._exec(*args, **kwargs)

    def start(self) -> None:
        """ Start a new thread to service this engine until program exit. Must be daemonic to die with the program. """
        Thread(target=self._loop, daemon=True).start()

    def _loop(self) -> None:
        """ Execute commands in our queue. They have been sent by other threads, so we do not need to echo them. """
        while True:
            self.call_ext(self.get())

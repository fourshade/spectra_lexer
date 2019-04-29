from traceback import TracebackException
from typing import Any, Callable, Tuple


class Runtime:

    _executor: Callable[[Tuple[str, tuple, dict]], Any] = None  # Callable that ultimately executes commands.

    def __init__(self, executor):
        self._executor = executor

    def __call__(self, key:str, args:tuple, kwargs:dict):
        """ Run all commands matching a key and return the last result. Handle exceptions that make it back here.
            Qt will crash if exceptions propagate back to it; do not allow this under normal circumstances. """
        try:
            return self._executor(key, args, kwargs)
        except Exception as exc_value:
            # Exception handling is done, like anything else, by calling components.
            # Some apps may lock stderr while running, and a GUI can only print exceptions after setup.
            # Unhandled exceptions in an exception handler are fatal. They should return instead of raise.
            return self._executor("exception", (exc_value,), {})

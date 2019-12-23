from traceback import format_exception
from types import TracebackType
from typing import Any, Callable, Type


class ExceptionManager:
    """ Delegates exception handling and logging to other objects. """

    def __init__(self, max_frames=20) -> None:
        self._max_frames = max_frames  # Maximum number of stack frames to write to logs.
        self._handlers = []            # Contains all registered exception handler callbacks.
        self._loggers = []             # Contains all registered stack trace loggers.

    def add_handler(self, handler:Callable[[BaseException], Any]) -> None:
        """ Add a callback to receive the exception. This callback should return True if the exception was handled. """
        self._handlers.append(handler)

    def _call_handlers(self, exc:BaseException) -> None:
        """ Call each exception handler in turn until one (if any) returns True. """
        for handle_exception in self._handlers:
            if handle_exception(exc):
                break

    def add_logger(self, logger:Callable[[str], Any]) -> None:
        """ Add a string callback to log exception stack traces. Its return value is ignored. """
        self._loggers.append(logger)

    def _call_loggers(self, tb_text:str) -> None:
        """ Write a stack trace to each logger in turn. """
        for log in self._loggers:
            log(tb_text)

    def on_exception(self, exc:BaseException) -> None:
        """ Call the exception hook given only an exception object. """
        self.excepthook(type(exc), exc, exc.__traceback__)

    def excepthook(self, exc_type:Type[BaseException], exc_value:BaseException, exc_traceback:TracebackType) -> None:
        """ Send an exception to handlers and write the stack trace to loggers.
            This method is designed to directly replace sys.excepthook. """
        tb_lines = format_exception(exc_type, exc_value, exc_traceback, limit=self._max_frames)
        tb_text = "".join(tb_lines)
        self._call_loggers(tb_text)
        self._call_handlers(exc_value)

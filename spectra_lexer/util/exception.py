from traceback import format_exception
from types import TracebackType
from typing import Any, Callable, Type, Union

# Exception handler argument types. 2/3 of it is redundant; the signature is kept for historical reasons.
ExceptionArgs = (Type[BaseException], BaseException, TracebackType)
ExceptionStarArgs = Union[ExceptionArgs]  # *args type hint for same.


class ExceptionHandler:
    """ Generic exception handler. Same signature as __exit__.
        Should return True if the exception was handled. May be used to replace sys.excepthook. """

    def __call__(self, *args:ExceptionStarArgs) -> bool:
        raise NotImplementedError


class ExceptionEater(ExceptionHandler):
    """ GULP. """

    def __call__(self, *_) -> bool:
        return True


class ExceptionLogger(ExceptionHandler):
    """ Writes exception tracebacks to arbitrary callables. """

    def __init__(self, logger:Callable[[str], Any], *, max_frames=20) -> None:
        self._logger = logger          # String logger callable. Its return value is ignored.
        self._max_frames = max_frames  # Maximum number of stack frames to write.

    def __call__(self, *args:ExceptionStarArgs) -> bool:
        """ Write the stack trace to the logger. This does *not* count as handling the exception. """
        tb_lines = format_exception(*args, limit=self._max_frames)
        tb_text = "".join(tb_lines)
        self._logger(tb_text)
        return False


class CompositeExceptionHandler(ExceptionHandler):
    """ Delegates exception handling to other handlers in order of addition. """

    def __init__(self) -> None:
        self._handlers = []  # List of all child exception handler callbacks.

    def add(self, handler:ExceptionHandler) -> None:
        """ Add a new callback to receive the exception. """
        self._handlers.append(handler)

    def __call__(self, *args:ExceptionStarArgs) -> bool:
        """ Call each exception handler in turn until one (if any) returns True. """
        for handle_exception in self._handlers:
            if handle_exception(*args):
                return True
        return False

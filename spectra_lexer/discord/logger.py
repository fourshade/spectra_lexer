import sys
from traceback import format_exception
from typing import Callable

LineLogger = Callable[[str], None]  # Line-based string callable used for log messages.


def log_at_level(level:int, default_exc_info=None) -> Callable[..., None]:
    def _try_log(self, msg, *args, exc_info=default_exc_info) -> None:
        if level >= self._level:
            self._log(msg, args, exc_info)
    return _try_log


class Logger:
    """ Skeleton replacement for logging module to log all activity to one callable. """

    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
    DISABLED = 5

    def __init__(self) -> None:
        self._handler = print
        self._level = self.INFO

    def setHandler(self, hdlr:LineLogger) -> None:
        self._handler = hdlr

    def setLevel(self, level:int) -> None:
        self._level = level

    def disable(self) -> None:
        self._level = self.DISABLED

    def _log(self, msg, args:tuple, exc_info=None) -> None:
        msg = str(msg)
        if args:
            msg = msg % args
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
            msg = ''.join([msg, '\n', *format_exception(*exc_info)])
        self._handler(msg.strip())

    debug = log_at_level(DEBUG)
    info = log_at_level(INFO)
    warning = log_at_level(WARNING)
    error = log_at_level(ERROR)
    critical = log_at_level(CRITICAL)
    exception = log_at_level(ERROR, True)


log = Logger()

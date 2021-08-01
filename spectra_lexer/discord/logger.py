from traceback import format_exc
from typing import Callable

LineLogger = Callable[[str], None]


class Logger:
    """ Skeleton replacement for logging module. """

    def __init__(self, logger:Callable[[str], None]) -> None:
        self.line_logger = logger  # Line-based string callable used for log messages.

    def debug(self, *args) -> None:
        pass

    def info(self, message:str, *args) -> None:
        self.line_logger((message % args) if args else message)

    warning = error = info

    def exception(self, *args) -> None:
        self.error(*args)
        self.line_logger(format_exc())


log = Logger(print)

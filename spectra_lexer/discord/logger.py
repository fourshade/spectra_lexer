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
        self.line_logger(message % args)

    def warning(self, message:str, *args) -> None:
        self.line_logger(message % args)

    def exception(self, message:str, *args) -> None:
        self.line_logger((message % args) + '\n' + format_exc())


log = Logger(print)

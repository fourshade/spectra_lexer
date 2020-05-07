from threading import Lock
from time import strftime
from typing import TextIO


class StreamLogger:
    """ Basic logger class. Writes to pre-opened text streams. Implements basic thread-safety. """

    def __init__(self, *streams:TextIO, time_fmt="%b %d %Y %H:%M:%S", repeat_mark="*") -> None:
        self._streams = streams          # One or more writable/appendable text streams for logging.
        self._time_fmt = time_fmt        # Format string for timestamps using time.strftime.
        self._repeat_mark = repeat_mark  # Mark for repeated messages (to save space).
        self._lock = Lock()              # Lock to ensure only one thread writes to the streams at a time.
        self._last_message = ""          # Most recently logged message string.

    def _replace_if_duplicate(self, message:str) -> str:
        """ Replace <message> with a short 'repeat' mark if identical to the last message. """
        if message == self._last_message:
            message = self._repeat_mark
        else:
            self._last_message = message
        return message

    def _add_timestamp(self, message:str) -> str:
        """ Add a timestamp before <message>. """
        t_str = strftime(self._time_fmt)
        return f'[{t_str}]: {message}\n'

    def _write_all(self, message:str) -> None:
        """ Log a message with all registered streams. """
        with self._lock:
            for stream in self._streams:
                try:
                    # Flush after every write so that messages don't get lost in the buffer on a crash.
                    stream.write(message)
                    stream.flush()
                except Exception:
                    # An exception here most likely means everything is FUBAR.
                    # At this point, we're in damage control mode. Keep trying streams no matter what.
                    continue

    def log(self, message:str) -> None:
        """ Filter, timestamp, and log a message with all streams. """
        message = self._replace_if_duplicate(message)
        message = self._add_timestamp(message)
        self._write_all(message)

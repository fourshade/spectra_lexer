import sys
from threading import Lock
from time import strftime
from typing import TextIO


class StreamLogger:
    """ Basic logger class. Writes to pre-opened text streams. Implements basic thread-safety. """

    def __init__(self, *streams:TextIO, time_fmt="[%b %d %Y %H:%M:%S]: ", repeat_mark="*") -> None:
        self._streams = streams          # One or more writable/appendable text streams for logging.
        self._time_fmt = time_fmt        # Format for timestamps using time.strftime. If None, do not add timestamps.
        self._repeat_mark = repeat_mark  # Mark to replace repeated messages. If None, log all messages fully.
        self._last_message = ""          # Most recent unique message string.
        self._lock = Lock()              # Lock to ensure only one thread writes to the streams at a time.

    def _replace_if_duplicate(self, message:str) -> str:
        """ Replace <message> with a short 'repeat' mark if identical to the last message to save space. """
        if message == self._last_message:
            message = self._repeat_mark
        else:
            self._last_message = message
        return message

    def _add_timestamp(self, message:str) -> str:
        """ Add a timestamp with the current time before <message>. """
        return strftime(self._time_fmt) + message

    def _write_all(self, message:str) -> None:
        """ Write <message> to each stream in turn. """
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
        """ Filter, timestamp, and write <message> to all log streams with a trailing newline. """
        if self._repeat_mark is not None:
            message = self._replace_if_duplicate(message)
        if self._time_fmt is not None:
            message = self._add_timestamp(message)
        self._write_all(message + '\n')


def open_logger(*filenames:str, encoding='utf-8', to_stdout=False, to_stderr=False, **kwargs) -> StreamLogger:
    """ Open a logger that appends to text files and/or prints to system streams.
        Log files will remain open until the program is closed. """
    streams = [open(f, 'a', encoding=encoding) for f in filenames]
    if to_stdout:
        streams.append(sys.stdout)
    if to_stderr:
        streams.append(sys.stderr)
    return StreamLogger(*streams, **kwargs)

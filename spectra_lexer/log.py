import time
from threading import Lock
from typing import TextIO


class StreamLogger:
    """ Basic logger class. Writes to pre-opened text streams. Implements basic thread-safety. """

    def __init__(self, *streams:TextIO, lock=None) -> None:
        self._streams = [*streams]   # List of writable/appendable text streams for logging.
        self._lock = lock or Lock()  # Lock to ensure only one thread writes to the streams at a time.
        self._last_msg = ""          # Most recently logged string.

    def add_stream(self, stream:TextIO) -> None:
        """ Add a text stream for logging. """
        with self._lock:
            self._streams.append(stream)

    def log(self, msg:str) -> None:
        """ Log a timestamped message with all registered streams. Omit details if identical to the last message. """
        with self._lock:
            if msg == self._last_msg:
                msg = "*"
            else:
                self._last_msg = msg
            t_str = time.strftime("%b %d %Y %H:%M:%S")
            entry = f'[{t_str}]: {msg}\n'
            for stream in self._streams:
                try:
                    # Flush after every write so that messages don't get lost in the buffer on a crash.
                    stream.write(entry)
                    stream.flush()
                except Exception:
                    # An exception here most likely means everything is FUBAR.
                    # At this point, we're in damage control mode. Keep trying streams no matter what.
                    continue

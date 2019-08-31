import time
from typing import TextIO


class StreamLogger:
    """ Basic logger class. Writes to pre-opened text streams. """

    def __init__(self, *streams:TextIO) -> None:
        self._streams = [*streams]  # List of writable/appendable text streams for logging.
        self._last_msg = ""         # Most recently logged string.

    def add_stream(self, stream:TextIO) -> None:
        """ Add a text stream for logging. """
        self._streams.append(stream)

    def log(self, msg:str) -> None:
        """ Log a timestamped message with all registered streams. Omit details if identical to the last message.
            Flush every stream after write so logs don't disappear after a crash. """
        if msg == self._last_msg:
            msg = "*"
        else:
            self._last_msg = msg
        t_str = time.strftime("%b %d %Y %H:%M:%S")
        entry = f'[{t_str}]: {msg}\n'
        for stream in self._streams:
            try:
                stream.write(entry)
                stream.flush()
            except Exception:
                # An exception here most likely means everything is FUBAR.
                # At this point, we're in damage control mode. Keep trying streams no matter what.
                pass

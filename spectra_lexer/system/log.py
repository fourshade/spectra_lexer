import os
import time
from typing import List, TextIO


class StreamLogger:

    streams: List[TextIO]  # List of writable/appendable text streams for logging.
    _last_msg: str = ""    # Most recently logged string.

    def __init__(self, *streams:TextIO):
        self.streams = [*streams]

    def __call__(self, msg:str) -> None:
        """ Log a message with all streams. Omit details if identical to the last message.
            Flush every stream after write so logs don't disappear after a crash. """
        if msg == self._last_msg:
            msg = "*"
        else:
            self._last_msg = msg
        t_str = time.strftime("%b %d %Y %H:%M:%S")
        entry = f'[{t_str}]: {msg}\n'
        for stream in self.streams:
            try:
                stream.write(entry)
                stream.flush()
            except Exception:
                pass

    def add_path(self, path:str) -> None:
        """ Open the specified file and add it as a text stream for logging. Close it on application exit. """
        directory = os.path.dirname(path) or "."
        os.makedirs(directory, exist_ok=True)
        fp = open(path, 'a')
        self.streams.append(fp)

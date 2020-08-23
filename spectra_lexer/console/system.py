from contextlib import ContextDecorator
import ctypes
from io import TextIOBase
import os
import sys
from threading import Thread
from types import SimpleNamespace
from typing import Any, Callable

Runnable = Callable[[], Any]


def text_pipe(*, encoding='utf-8'):
    """ Open file objects for a pipe in text mode. """
    read_fd, write_fd = os.pipe()
    fp_in = open(read_fd, 'r', encoding=encoding)
    fp_out = open(write_fd, 'w', encoding=encoding)
    return fp_in, fp_out


class TextIOWriter(TextIOBase):
    """ Wraps a string callable as a writable stream. """

    def __init__(self, write_callback:Callable[[str], Any]) -> None:
        self._write_callback = write_callback  # Callback with one positional string argument.

    def write(self, text:str) -> int:
        self._write_callback(text)
        return len(text)

    def writable(self) -> bool:
        return True


class SysRedirector(SimpleNamespace, ContextDecorator):
    """ Namespace of attributes to override in the sys module while inside a 'with' block. """

    def _swap(self, *_) -> None:
        """ Swap out attributes on the sys module to redirect the standard streams.
            This operation is symmetrical; calling it again will restore the original attributes. """
        myvars = vars(self)
        sysvars = vars(sys)
        replaced = {k: sysvars[k] for k in myvars}
        sysvars.update(myvars)
        myvars.update(replaced)

    __enter__ = __exit__ = _swap


class Console:
    """ Contains streams and a thread for running an asynchronous console application. """

    _func: Runnable  # Console application callable, set by start(). Takes no arguments.

    def __init__(self, file_out:TextIOBase) -> None:
        fp_in, fp_out = text_pipe()
        redirector = SysRedirector(stdin=fp_in, stdout=file_out, stderr=file_out)
        fp_in.read = redirector(fp_in.read)
        fp_in.readline = redirector(fp_in.readline)
        target = redirector(self._run)
        self._thread = Thread(target=target, daemon=True)
        self._fp_in = fp_in    # Read end of pipe.  The thread spends most of its time blocked here.
        self._fp_out = fp_out  # Write end of pipe. Must be flushed for the read end to see anything.

    def _run(self) -> None:
        """ Run the application and close the pipe when finished. """
        with self._fp_in, self._fp_out:
            self._func()

    def start(self, func:Runnable) -> None:
        """ Start the thread running <func> as a console program. """
        self._func = func
        self._thread.start()

    def send(self, text:str) -> None:
        """ Write user input and flush. Ignore write errors due to the pipe closing. """
        try:
            self._fp_out.write(text)
            self._fp_out.flush()
        except OSError:
            pass

    def _raise_async(self, exc_type:type) -> bool:
        """ Raise an exception type inside the thread asynchronously. Return True if successful.
            Black magic with ctypes seems to be the only way, so extra care must be taken. """
        if not isinstance(exc_type, type):
            raise TypeError("Only types can be raised (not instances)")
        if not issubclass(exc_type, BaseException):
            raise TypeError("Only subclasses of BaseException can be raised")
        # The thread must be active to receive exceptions.
        if not self._thread.is_alive():
            return False
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(self._thread.ident, ctypes.py_object(exc_type))
        return (res == 1)

    def interrupt(self) -> bool:
        """ Raise KeyboardInterrupt inside the thread. """
        return self._raise_async(KeyboardInterrupt)

    def terminate(self) -> bool:
        """ Raise SystemExit inside the thread to make it exit if currently processing.
            The pipe must be closed first to stop blocking reads. """
        self._fp_out.close()
        return self._raise_async(SystemExit)

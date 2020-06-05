""" General classes for lower-level Qt system operations. """

from queue import Queue
import sys
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject, QThread


class QtExceptionHook(QObject):
    """ Traps exceptions for the Qt GUI and emits them as signals.
        Useful since Qt may crash if Python exceptions propagate back to the event loop. """

    _sig_exception = pyqtSignal([BaseException])  # Sent when a Python exception reaches the Qt event loop.

    def __init__(self, *, chain_hooks=True) -> None:
        super().__init__()
        self._prev_excepthook = None     # Previous value of sys.excepthook.
        self._chain_hooks = chain_hooks  # If True, call the previous exception hook once we're done.

    def _excepthook(self, exc_type, exc_value:BaseException, exc_traceback) -> None:
        """ Emit a Python exception as a Qt signal and optionally chain the call to the last hook. """
        self._sig_exception.emit(exc_value)
        if self._chain_hooks:
            self._prev_excepthook(exc_type, exc_value, exc_traceback)

    def connect(self, callback:Callable[[BaseException], None]) -> None:
        """ Connect an exception handler <callback> to the signal. It should only take the exception value itself.
            Save the original value of sys.excepthook for chaining and disconnection. """
        if self._prev_excepthook is not None:
            raise RuntimeError("Exception hook already connected.")
        self._prev_excepthook = sys.excepthook
        self._sig_exception.connect(callback)
        sys.excepthook = self._excepthook

    def disconnect(self) -> None:
        """ Disconnect the signal and restore sys.excepthook to its original value. """
        if self._prev_excepthook is None:
            raise RuntimeError("Exception hook not connected.")
        sys.excepthook = self._prev_excepthook
        self._sig_exception.disconnect()
        self._prev_excepthook = None


class QtTaskExecutor(QObject):
    """ Manages a queue that executes GUI tasks on the main thread and long-running operations on a worker thread. """

    _sig_call_main = pyqtSignal([object, tuple])  # Allows this thread to execute functions on the main event loop.

    def __init__(self) -> None:
        super().__init__()
        self._q = Queue()
        self._thread = QThread()

    def on_main(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on the main thread. """
        self._q.put((self._sig_call_main.emit, func, args))

    def on_worker(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on the worker thread. """
        self._q.put((func, *args))

    def _run(self) -> None:
        """ Loop through the queue and execute each item in turn. """
        while True:
            func, *args = self._q.get()
            func(*args)

    def start(self) -> None:
        """ Start the worker thread and connect the signal that applies functions on the main thread. """
        self._sig_call_main.connect(lambda func, args: func(*args))
        self._thread.run = self._run
        self._thread.start()

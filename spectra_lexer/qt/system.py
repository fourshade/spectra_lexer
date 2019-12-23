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


class QtSignalCaller(QObject):
    """ Allows any thread to execute functions on this object's event loop using a Qt signal. """

    _sig_call = pyqtSignal([object, tuple, dict])

    def __init__(self) -> None:
        super().__init__()
        self._sig_call.connect(lambda func, args, kwargs: func(*args, **kwargs))

    def __call__(self, func:Callable=None, *args, **kwargs) -> None:
        if func is not None:
            self._sig_call.emit(func, args, kwargs)


class QtAsyncDispatcher:
    """ Executes long-running operations on a separate thread. """

    def __init__(self) -> None:
        self._q = Queue()
        self._thread = QThread()
        self._call_on_main = QtSignalCaller()

    def dispatch(self, func:Callable, *args, on_start:Callable=None, on_finish:Callable=None) -> None:
        """ Add <func> as a task with the given <args> and send back results using a Qt signal.
            <on_start>, if given, will be called on the main thread with no arguments just before the task starts.
            <on_finish>, if given, must accept the return value of this function as its only argument. """
        self._q.put((func, args, on_start, on_finish))
        if not self._thread.isRunning():
            self._thread.run = self._run
            self._thread.start()

    def _run(self) -> None:
        """ Loop through the queue and execute each item in turn. """
        while True:
            func, args, on_start, on_finish = self._q.get()
            self._call_on_main(on_start)
            value = func(*args)
            self._call_on_main(on_finish, value)

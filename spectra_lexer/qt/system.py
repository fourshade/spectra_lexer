""" General classes for lower-level Qt system operations. """

from threading import Thread
from typing import Any, Callable

from PyQt5.QtCore import pyqtSignal, QObject


class QtExceptionTrap(QObject):
    """ Traps exceptions for the Qt GUI and emits them as signals. """

    _sig_traceback = pyqtSignal([Exception])  # Sent when an exception is encountered in protected code.

    def __init__(self) -> None:
        super().__init__()
        self.connect = self._sig_traceback.connect

    def __enter__(self) -> None:
        """ Qt may crash if Python exceptions propagate back to the event loop.
            Enter this object as a context manager to prevent exceptions from escaping the following code. """
        return None

    def __exit__(self, _, exc:BaseException, *args) -> bool:
        """ Emit any thrown exception as a Qt signal.
            Do NOT catch BaseExceptions - these are typically caused by the user wanting to exit the program. """
        if isinstance(exc, Exception):
            self._sig_traceback.emit(exc)
            return True

    def wrap(self, func:Callable) -> Callable[..., None]:
        """ Wrap a callable to trap and emit any exceptions propagating from it. It will not return a value. """
        def trapped_call(*args, **kwargs) -> None:
            with self:
                func(*args, **kwargs)
        return trapped_call


class QtAsyncDispatcher(QObject):
    """ Enables long-running operations on separate threads while keeping the GUI responsive. """

    _sig_done = pyqtSignal([object, object])  # Internal signal; used to send results back to the main thread.

    def __init__(self, exc_trap:QtExceptionTrap) -> None:
        super().__init__()
        self._exc_trap = exc_trap
        self._sig_done.connect(self._done)

    def dispatch(self, *args, **kwargs) -> None:
        """ Call a function on a new thread. """
        Thread(target=self._run, args=args, kwargs=kwargs, daemon=True).start()

    def _run(self, func:Callable, *args, callback:Callable=None, **kwargs) -> None:
        """ Run <func> with the given args/kwargs and send back results using a Qt signal.
            <callback>, if given, must accept the return value of this function as its only argument. """
        with self._exc_trap:
            value = func(*args, **kwargs)
            if callback is not None:
                self._sig_done.emit(callback, value)

    def _done(self, callback:Callable, value:Any) -> None:
        """ Call the callback on the main thread once the task is done. """
        with self._exc_trap:
            callback(value)

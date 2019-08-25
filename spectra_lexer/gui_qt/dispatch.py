""" Module for controlling resource loading and other long-running operations independent of the GUI thread. """

from threading import Thread
from typing import Any, Callable

from PyQt5.QtCore import pyqtSignal, QObject


class AsyncThreadLoader(QObject):
    """ Enables long-running operations while keeping the GUI responsive (though disabled). """

    _sig_exception = pyqtSignal(Exception)
    _sig_done = pyqtSignal([str, object, object])
    _set_enabled: Callable[[bool], None]  # Function to call with a boolean to set GUI enabled states.
    _show_message: Callable[[str], None]  # Optional callback to show status messages on task start and finish.

    def __init__(self, enable_callback:Callable[[bool],None], msg_callback:Callable[[str],None],
                 exc_handler:Callable[[Exception],None]) -> None:
        super().__init__()
        self._set_enabled = enable_callback
        self._show_message = msg_callback
        self._sig_exception.connect(exc_handler)
        self._sig_done.connect(self._on_async_done)

    def run(self, func:Callable, *args, callback:Callable=None,
            msg_in:str="Loading...", msg_out:str="Loading complete.") -> None:
        """ Call <func> on a new thread and disable the GUI while the thread is busy.
            <callback>, if given, must accept the return value of this function as its only argument. """
        self._set_enabled(False)
        self._show_message(msg_in)
        Thread(target=self._run, args=(func, args, msg_out, callback), daemon=True).start()

    def _run(self, func:Callable, args:tuple, msg_out:str, callback:Callable) -> None:
        """ Run a function and send back results using a Qt signal. """
        with self:
            value = func(*args)
            self._sig_done.emit(msg_out, callback, value)

    def _on_async_done(self, msg_out:str, callback:Callable, value:Any) -> None:
        """ Re-enable the GUI once the thread is clear, then call the callback (in that order). """
        self._show_message(msg_out)
        self._set_enabled(True)
        if callback is not None:
            with self:
                callback(value)

    def protect(self, func:Callable) -> Callable:
        """ C frameworks such as Qt may crash if Python exceptions propagate back to them.
            This thread-safe wrapper takes care of exceptions before they make it back to the Qt event loop. """
        def call(*args, **kwargs) -> Any:
            with self:
                return func(*args, **kwargs)
        return call

    def __enter__(self) -> None:
        return None

    def __exit__(self, _, exc:BaseException, *args) -> bool:
        """ Catch any exception thrown by the wrapped code and send it off for logging/printing using the signal.
            Do NOT catch BaseExceptions - these are typically caused by the user wanting to exit the program. """
        if isinstance(exc, Exception):
            self._sig_exception.emit(exc)
            return True

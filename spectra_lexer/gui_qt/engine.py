from queue import Queue
from threading import Thread
from typing import Callable

from PyQt5.QtCore import pyqtSignal, QObject


class EngineWrapper(QObject):

    _obj: object
    _exc_handler: Callable
    _queue: Queue

    def __init__(self, obj:object, exc_handler:Callable=str):
        """ Assemble the wrapper with an exception handler and start a new thread to service it until program exit. """
        super().__init__()
        self._obj = obj
        self._exc_handler = exc_handler
        self._queue = Queue()
        self.return_signal.connect(self.return_call)
        Thread(target=self.loop, daemon=True).start()

    def loop(self) -> None:
        """ If there's an exception and we're at the top level, try to handle it with the exception command.
            C frameworks may crash if exceptions propagate back to them, so try to handle them here if possible.
            Do NOT handle BaseExceptions - these are typically caused by the user wanting to exit the program. """
        while True:
            func, args, kwargs, callback = self._queue.get()
            try:
                value = func(*args, **kwargs)
                if callback is not None:
                    self.return_signal.emit((callback, value))
            except Exception as exc:
                self.return_signal.emit((self._exc_handler, exc))

    def __getattr__(self, attr:str):
        func = getattr(self._obj, attr)
        if not callable(func):
            return func
        def put(*args, qt_callback=None, **kwargs) -> None:
            self._queue.put((func, args, kwargs, qt_callback))
        return put

    def return_call(self, params:tuple) -> None:
        """ A signal-slot connection for transferring tuples back to the main thread. """
        callback, value = params
        callback(value)

    # Signals
    return_signal = pyqtSignal(tuple)

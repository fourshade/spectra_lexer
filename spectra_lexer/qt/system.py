""" General classes for low-level Qt system operations. """

from queue import Queue
from typing import Callable, NoReturn

from PyQt5.QtCore import pyqtSignal, QThread


def _apply(func:Callable, args:tuple) -> None:
    func(*args)


def _raise(exc:Exception) -> NoReturn:
    raise exc


class QtTaskExecutor(QThread):
    """ Worker thread that executes long-running operations from a queue. """

    _sig_call_main = pyqtSignal([object, tuple])  # Allows this thread to apply functions on the main event loop.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._q = Queue()
        self._sig_call_main.connect(_apply)

    def on_worker(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on this thread. """
        self._q.put((func, *args))

    def on_main(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on the main thread. """
        self._q.put((self._sig_call_main.emit, func, args))

    def run(self) -> None:
        """ Loop through the queue and execute each task in turn.
            The behavior when exceptions kill threads is unpredictable. Reraise all exceptions on the main thread. """
        while True:
            try:
                func, *args = self._q.get()
                func(*args)
            except Exception as exc:
                self.on_main(_raise, exc)

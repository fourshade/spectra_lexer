""" General classes for low-level Qt system operations. """

from queue import Queue
from typing import Callable, NoReturn

from PyQt5.QtCore import pyqtSignal, QCoreApplication, QObject, QThread


def _apply(func:Callable, args:tuple) -> None:
    func(*args)


def _raise(exc:Exception) -> NoReturn:
    raise exc


class QtTaskExecutor(QObject):
    """ Manages a queue that executes long-running operations on a worker thread. """

    _sig_call_main = pyqtSignal([object, tuple])  # Allows this thread to apply functions on the main event loop.

    def __init__(self) -> None:
        super().__init__()
        self._q = Queue()
        self._thread = QThread()

    def on_worker(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on the worker thread. """
        self._q.put((func, *args))

    def on_main(self, func:Callable, *args) -> None:
        """ Add <func> as a task with the given <args> to be called on the main thread. """
        self._q.put((self._sig_call_main.emit, func, args))

    def _run(self) -> None:
        """ Loop through the queue and execute each item in turn.
            The behavior when exceptions kill threads is unpredictable. Reraise all exceptions on the main thread. """
        while True:
            try:
                func, *args = self._q.get()
                func(*args)
            except Exception as exc:
                self.on_main(_raise, exc)

    def start(self) -> None:
        """ Start the worker thread and connect the signal that applies functions on the main thread.
            GUI events may misbehave unless explicitly processed before the worker thread takes the GIL. """
        q_app = QCoreApplication.instance()
        q_app.processEvents()
        self._sig_call_main.connect(_apply)
        self._thread.run = self._run
        self._thread.start()

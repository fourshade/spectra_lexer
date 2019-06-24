""" Main entry point for Spectra's interactive GUI application. """

from spectra_lexer import resource, steno, system, view
from spectra_lexer.core.app import Application
from spectra_lexer.core.engine import Engine, ThreadedEngineGroup


class ViewApplication(Application):
    """ Abstract base class for multi-threaded interactive steno applications. """

    def _class_paths(self) -> list:
        """ For multi-threaded applications, there is a separate path list for each thread.
            Run the primary task on the main thread, and the other layers on a worker thread. """
        return [self._main_class_paths(), self._worker_class_paths()]

    def _main_class_paths(self) -> list:
        raise NotImplementedError

    def _worker_class_paths(self) -> list:
        return [system, resource, steno, view]

    def _engine(self, **kwargs) -> Engine:
        """ We use multiple threads to avoid overwhelming the main thread with heavy computations. """
        return ThreadedEngineGroup(*self._components, **kwargs)

from spectra_lexer import resource, steno, system, view
from spectra_lexer.core.app import Application
from spectra_lexer.core.engine import Engine, ThreadedEngineGroup


class ViewApplication(Application):
    """ Abstract base class for multi-threaded interactive steno applications. """

    def _worker_class_paths(self) -> list:
        """ We run the primary task on the main thread, and the other layers on a worker thread. """
        return [system, resource, steno, view]

    def _build_engine(self, **kwargs) -> Engine:
        """ For multi-threaded applications, there is a separate path list for each thread. """
        main_group = self._components
        worker_group = self._build_components(self._worker_class_paths())
        self._components = [*main_group, *worker_group]
        return ThreadedEngineGroup(main_group, worker_group, **kwargs)

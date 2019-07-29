from .view import ViewManager
from spectra_lexer.core.app import Application
from spectra_lexer.core import Engine, ThreadedEngineGroup
from spectra_lexer.resource import ResourceManager
from spectra_lexer.steno import StenoAnalyzer


class ViewApplication(Application):
    """ Abstract base class for multi-threaded interactive steno applications. """

    def _build_workers(self) -> list:
        """ We run the primary task on the main thread, and the other layers on a worker thread. """
        return [*super()._build_components(), ResourceManager(), StenoAnalyzer(), ViewManager()]

    def _build_components(self) -> list:
        return []

    def _build_engine(self, components:list, **kwargs) -> Engine:
        """ For multi-threaded applications, there is a separate path list for each thread. """
        main_group = components[:]
        worker_group = self._build_workers()
        components += worker_group
        return ThreadedEngineGroup(main_group, worker_group, **kwargs)

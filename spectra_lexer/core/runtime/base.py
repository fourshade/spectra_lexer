from typing import Iterable, Callable

from .engine import Engine, MainEngine, SimpleEngine, ThreadedEngine
from .executor import Executor
from spectra_lexer.core.factory import ComponentFactory


class Runtime:
    """ Simple single-threaded type base runtime class for the Spectra program.
        Routes messages and data structures between all constituent components using an engine. """

    _class_paths: Iterable      # Modules containing component classes to instantiate.
    _factory: ComponentFactory  # Factory to build components from class paths and bind them to commands.

    def __init__(self, class_paths:Iterable):
        self._class_paths = class_paths
        self._factory = ComponentFactory()

    def setup(self) -> Callable:
        """ Build the engine using the factory and return a top-level callable. """
        engine = self._build_engine()
        # Use the callable to complete setup by loading resources.
        self._factory.setup(engine.call)
        return engine.call

    def _build_engine(self) -> Engine:
        """ By default, the standard single-threaded engine is used. """
        return self._assemble_engine(SimpleEngine, self._class_paths)

    def _assemble_engine(self, engine_cls:type, class_paths:Iterable):
        """ Assemble an engine using components from class paths and the factory. """
        executor = Executor()
        engine = engine_cls(executor)
        commands = self._factory.build(class_paths, engine.call)
        executor.add_commands(commands)
        return engine


class ThreadedRuntime(Runtime):
    """ Runtime class for components grouped into threads. The passthrough method should take a function
        and return something that *other* threads can call to run that function on the main thread. """

    _worker_class_groups: Iterable[Iterable]  # A series of module groups, one for each thread.
    _passthrough: Callable                    # Must notify the main thread and pass a single tuple argument.

    def __init__(self, main_class_paths:Iterable, worker_class_groups:Iterable[Iterable], passthrough:Callable):
        super().__init__(main_class_paths)
        self._worker_class_groups = worker_class_groups
        self._passthrough = passthrough

    def _build_engine(self) -> Engine:
        """ Create the main engine using the first group of class paths and the passthrough method. """
        main_engine = self._assemble_engine(MainEngine, self._class_paths)
        main_engine.set_passthrough(self._passthrough)
        # Create a child engine to service each group of worker class paths and connect each one to the main engine.
        for worker_class_paths in self._worker_class_groups:
            child = self._assemble_engine(ThreadedEngine, worker_class_paths)
            main_engine.connect(child)
        # All top-level calls go through the main engine, as if it were the only one.
        return main_engine

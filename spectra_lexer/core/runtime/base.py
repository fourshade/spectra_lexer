from typing import Callable

from ..component import ComponentGroup
from .engine import Engine, ThreadedEngine
from .executor import Executor


class Runtime:
    """ Simple single-threaded type base runtime class for the Spectra program.
        Routes messages and data structures between all constituent components using an engine. """

    def setup(self, *args) -> Callable:
        """ Build the engine and return a top-level callable. """
        return self._assemble_engine(Engine, *args).call

    def _assemble_engine(self, engine_cls:type, components:ComponentGroup):
        """ Assemble an engine using components from class paths and the factory. """
        executor = Executor()
        engine = engine_cls(executor)
        components.connect(engine.call)
        executor.add_commands(components.bind())
        return engine


class ThreadedRuntime(Runtime):
    """ Runtime class for components grouped into threads. The passthrough method should take a function
        and return something that *other* threads can call to run that function on the main thread. """

    _passthrough: Callable  # Must notify the main thread and pass a single tuple argument.

    def __init__(self, passthrough:Callable):
        self._passthrough = passthrough

    def setup(self, components:ComponentGroup) -> Callable:
        """ Create engines to service each group of components. """
        all_engines = main_engine, *workers = [self._assemble_engine(ThreadedEngine, g) for g in components]
        # Add the passthrough method to the first engine only. All top-level calls go through this one.
        main_engine.set_passthrough(self._passthrough)
        # Connect everything together and start each engine.
        for engine in all_engines:
            for receiver in all_engines:
                if engine is not receiver:
                    engine.connect(receiver)
            engine.start()
        return main_engine.call

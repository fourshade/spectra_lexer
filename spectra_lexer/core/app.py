from typing import Callable, Iterable

from .component import ComponentFactory
from .engine import Engine, MainEngine, ThreadedEngine
from .runtime import Runtime


class Application:
    """ Simple single-threaded type base application class for the Spectra program.
        Routes messages and data structures between all constituent components using an engine. """

    DESCRIPTION: str = "Subclasses state their purpose here."
    CLASS_PATHS: Iterable = ()

    call: Callable = None

    def __init__(self):
        self._factory = ComponentFactory()

    def start(self, *args) -> None:
        """ Perform initial creation and loading of engine, components and resources. """
        self.call = self._engine_setup()
        # Initialize all resources in order. The packager will sort any dependencies out.
        self.call("init:", self._factory.get_ordered_resources())
        # Send a global object dict to debug tools, then run the app.
        self.call("res:debug", self._factory.get_all_objects())
        self.call("init_done")
        return self.run(*args)

    def _engine_setup(self) -> Callable:
        """ Create a new main engine with all components from class paths and return an engine callable. """
        return self._assemble_engine(Engine(), self.CLASS_PATHS)

    def _assemble_engine(self, engine:Engine, class_paths:Iterable) -> Callable:
        """ Assemble engine with a runtime using components from class paths. """
        engine_cb = engine.call
        components = self._factory.build(class_paths)
        executor = self._factory.bind(components, engine_cb)
        engine.set_runtime(Runtime(executor))
        return engine_cb

    def run(self, *args):
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError


class ThreadedApplication(Application):
    """ Application class for components grouped into threads. The passthrough method should take a function
        and return something that *other* threads can call to run that function on the main thread. """

    WORKER_CLASS_PATHS: Iterable[Iterable] = ()

    _ps_arg = Callable[[tuple], None]
    PASSTHROUGH: Callable[[_ps_arg], _ps_arg] = None

    def _engine_setup(self) -> Callable:
        """ Create the main engine, then create a child engine for each group of worker component classes. """
        engine = MainEngine()
        call = self._assemble_engine(engine, self.CLASS_PATHS)
        engine.set_passthrough(self.PASSTHROUGH)
        for worker_class_paths in self.WORKER_CLASS_PATHS:
            child = ThreadedEngine()
            self._assemble_engine(child, worker_class_paths)
            engine.connect(child)
        return call

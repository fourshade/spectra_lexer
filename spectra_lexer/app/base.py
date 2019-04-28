from .engine import Engine, MainEngine, ThreadedEngine
from .factory import ComponentFactory, CommandBinder, ModulePackage, package, ResourceBinder
from spectra_lexer import Component


class Application(Component):
    """ Simple single-threaded type base application class for the Spectra program.
        Routes messages and data structures between all constituent components using an engine. """

    DESCRIPTION: str = "Subclasses state their purpose here."
    CLASS_PATHS: list = []

    def __init__(self):
        super().__init__()
        self.components: ComponentFactory = ComponentFactory()
        self.commands: CommandBinder = CommandBinder()
        self.resources: ResourceBinder = ResourceBinder()
        self.modules: ModulePackage = ModulePackage()

    def start(self, *args) -> None:
        """ Perform initial creation and loading of engine, components and resources.
            The app cannot be constructed by the factory, so add it directly to the start of the path list. """
        self.setup(self, *self.CLASS_PATHS)
        d = {}
        for k, v in vars(self).items():
            if isinstance(v, package):
                d[k] = v.expand()
        self.engine_call("init:", self.resources.get_ordered())
        # Send the global dict to debug tools, then run the app.
        self.engine_call("res:debug", d)
        self.engine_call("init_done")
        return self.run(*args)

    def setup(self, *class_paths) -> None:
        """ Using a new main engine, add components from class paths. """
        self.assemble_engine(class_paths, Engine())

    def assemble_engine(self, class_paths, engine) -> None:
        """ Bind instances of component classes to their commands and resources with the engine callback. """
        engine_cb = engine.call
        for component in self.components(class_paths):
            component.engine_connect(engine_cb)
            self.resources.bind(component)
            for key, func in self.commands.bind(component, engine_cb):
                engine.add_command(key, func)

    def run(self, *args):
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError


class ThreadedApplication(Application):
    """ Application class for components grouped into threads. """

    WORKER_CLASS_PATHS: list = []
    PASSTHROUGH = lambda x: x

    def setup(self, *class_paths) -> None:
        """ Create the main engine, then create a child engine for each group of worker component classes. """
        engine = MainEngine(self.PASSTHROUGH)
        self.assemble_engine(class_paths, engine=engine)
        for worker_class_paths in self.WORKER_CLASS_PATHS:
            child = ThreadedEngine()
            self.assemble_engine(worker_class_paths, child)
            engine.connect(child)

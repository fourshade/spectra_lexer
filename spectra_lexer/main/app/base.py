from .engine import MainEngine, ThreadedEngine
from .factory import ComponentFactory
from spectra_lexer import Component


class Application(MainEngine):
    """ Base application class for the Spectra program. Routes messages and data structures between
        all constituent components using an engine. By default, it is a single-threaded type. """

    factory: ComponentFactory  # Makes components out of classes found in modules and packages.

    def __init__(self, *classes_or_modules):
        """ Create instances of all component classes found in modules and add them to a new engine. """
        self.factory = ComponentFactory()
        super().__init__(self.factory(classes_or_modules))

    def start(self, *args) -> object:
        """ Start the pipeline by processing options such as command line arguments from sys.argv. """
        self.load(**Component.RES)
        return self.run(*args)

    def load(self, **options) -> None:
        """ Perform initial loading of components. This may take a while depending on I/O. """
        self.call("start", **options)
        self.send_debug_vars(options)

    def send_debug_vars(self, options:dict) -> None:
        """ Send global variables such as components to debug components. """
        cmp_dict = self.factory.make_debug_dict()
        # Sort the components and send them as keywords in order.
        self.call("debug_vars", app=self, options=options, **dict(sorted(cmp_dict.items())))

    def run(self, *args) -> object:
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError


class ThreadedApplication(Application):
    """ Application class for components grouped into threads. Components within a single group can communicate freely;
        external communication is only allowed between the master and a child, and is strictly unidirectional. """

    child_engines: list  # List of child engine objects, each with its own thread and command queue.

    def __init__(self, main_classes, *worker_class_groups, **kwargs):
        """ Create the main engine, then create a child engine for each group of worker component classes. """
        super().__init__(*main_classes)
        self.child_engines = []
        for g in worker_class_groups:
            e = ThreadedEngine(self.factory(g), **kwargs)
            self.child_engines.append(e)
            # Start each child engine thread immediately.
            e.start()

    def call(self, key:str, *args, **kwargs) -> None:
        """ Call an application-wide command, first on the child engines, then a blocking call on ourselves. """
        cmd = key, args, kwargs
        for e in self.child_engines:
            e.send(cmd)
        self.call_main(cmd)

    def call_main(self, cmd:tuple) -> None:
        """ Call a command from a tuple on the main engine only. Only the MAIN thread should make it here. """
        key, args, kwargs = cmd
        super().call(key, *args, **kwargs)

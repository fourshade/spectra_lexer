from .engine import MainEngine, ThreadedEngine
from spectra_lexer import Component


class Application(MainEngine):
    """ Base application class for the Spectra program. Routes messages and data structures between
        all constituent components using an engine. By default, it is a single-threaded type. """

    def start(self, *args) -> object:
        """ Start the pipeline by processing options such as command line arguments from sys.argv. """
        self.load(components=self.components, **Component.RES)
        return self.run(*args)

    def load(self, **options) -> None:
        """ Perform initial loading of components. This may take a while depending on I/O. """
        self.call("start", **options)

    def run(self, *args) -> object:
        """ After everything else is ready, a primary task may be run. It may return a single value to main().
            A batch operation can run until complete, or a GUI event loop can run indefinitely. """
        raise NotImplementedError


class ThreadedApplication(Application):
    """ Application class for components grouped into threads. Components within a single group can communicate freely;
        external communication is only allowed between the master and a child, and is strictly unidirectional. """

    children: list  # List of child engine objects, each with its own thread and command queue.

    def __init__(self, main_classes, *worker_class_groups, **kwargs):
        """ Create the main engine, then create a child engine for each group of worker component classes. """
        super().__init__(*main_classes)
        self.children = [ThreadedEngine(*c, **kwargs) for c in worker_class_groups]
        # Add all components in children to our global list. Not exactly thread-safe, but it's for debug anyway.
        self.components += [c for e in self.children for c in e.components]
        # Start all child engine threads immediately.
        for e in self.children:
            e.start()

    def call(self, key:str, *args, **kwargs) -> None:
        """ Call an application-wide command, first on the child engines, then a blocking call on ourselves. """
        cmd = key, args, kwargs
        for e in self.children:
            e.send(cmd)
        self.main_call(cmd)

    def main_call(self, cmd:tuple) -> None:
        """ Call a command on the main engine only. Only the MAIN thread should make it here. """
        key, args, kwargs = cmd
        super().call(key, *args, **kwargs)

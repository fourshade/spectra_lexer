""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from spectra_lexer.core.mods import MainMod
from spectra_lexer.utils import nop


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name, bases):
        """ Start the namespace of every component with references to the main command decorators. """
        return MainMod.classes()

    @classmethod
    def build_from_paths(mcs, class_paths):
        """ Create and yield instances of all component subclasses found in <class_paths>.
            Class paths may include packages, modules, and classes themselves. """
        for path in class_paths:
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, mcs):
                    yield obj()


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).

    def engine_connect(self, engine_cb):
        """ Set the engine callback. """
        self.engine_call = engine_cb

    def __getstate__(self):
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}

""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from .mods import MainMod
from spectra_lexer.utils import nop


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name, bases):
        """ Start the namespace of every component with references to the main command decorators. """
        return MainMod.classes()

    @classmethod
    def from_paths(mcs, paths, engine_callback):
        """ Create, connect, and yield instances of all component subclasses found in <paths>.
            Class paths may include packages, modules, and classes themselves. """
        for p in paths:
            for obj in [p, *getattr(p, "__dict__", {}).values()]:
                if isinstance(obj, mcs):
                    cmp = obj()
                    cmp.engine_call = engine_callback
                    yield cmp


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).

    def __getstate__(self):
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}

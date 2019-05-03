""" Base module of the Spectra core package. Contains the most fundamental components. Don't touch anything... """

from .mods import ComponentModMeta
from spectra_lexer.utils import nop

MODS_BY_KEY = ComponentModMeta.get_classes_by_key()


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name, bases):
        """ Add references to the main mod decorators to every component. """
        return MODS_BY_KEY.copy()


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer object hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program.
        As such, it cannot depend on anything except pure utility functions. """

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

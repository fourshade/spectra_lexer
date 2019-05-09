""" Base module of the Spectra core package. Contains the most fundamental classes. Don't touch anything... """

from typing import Callable, Iterable, Tuple, List

from .mods import CommandMod, MainMod, ResourceMod, DebugPackageMod
from spectra_lexer.utils import nop, recurse


class ComponentMeta(type):
    """ Metaclass for all subclasses of Component. """

    def __prepare__(name:str, bases:tuple) -> dict:
        """ Start the namespace of every component with references to the main command decorators. """
        return MainMod.classes()


class Component(metaclass=ComponentMeta):
    """ Base class for any component that sends and receives commands from the Spectra engine.
        It is the root class of the Spectra lexer component hierarchy, being subclassed directly
        or indirectly by nearly every important (externally-visible) piece of the program. """

    engine_call = nop  # Default engine callback is a no-op (useful for testing individual components).

    def __getstate__(self) -> dict:
        """ Each component has a reference to the engine through self.engine_call, which respectively has a reference
            to almost everything else. Without intervention, if the pickler tries to pickle a component, it will
            follow the reference and attempt to pickle the engine, which results in pickling the entire program.
            Some parts are unavoidably unpickleable, so the reference chain must be stopped by removing engine_call.
            Unfortunately, this means no engine calls may be made by components after unpickling. """
        return {**vars(self), "engine_call": nop}


class ComponentGroup(list):
    """ Recursive grouping of engine components. """

    @classmethod
    def from_paths(cls, class_paths:Iterable):
        """ Create and include instances of all component subclasses found in <paths>.
            Class paths may include packages, modules, and classes themselves.
            If any are iterable, treat it as a distinct component group itself. """
        self = cls()
        for path in class_paths:
            if isinstance(path, Iterable):
                self.append(cls.from_paths(path))
            for obj in [path, *getattr(path, "__dict__", {}).values()]:
                if isinstance(obj, ComponentMeta):
                    self.append(obj())
        return self

    def connect(self, call:Callable) -> None:
        """ Recursively connect all components in the tree to the engine callback. """
        for cmp in recurse(self):
            cmp.engine_call = call

    def bind(self) -> List[Tuple[str, Callable]]:
        """ Recursively gather all engine commands from each component. """
        return [cmd for cmp in recurse(self) for cmd in CommandMod.bind_all(cmp)]

    def get_setup_commands(self) -> List[Tuple[str, dict]]:
        """ Get all required initialization commands and their arguments. """
        items = list(recurse(self))
        cmds = ResourceMod.init_commands(items)
        # Send a global dict with objects from all categories to debug tools.
        cmds.append(("res:debug", DebugPackageMod.package_all(items)))
        return cmds

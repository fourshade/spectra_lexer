from collections import defaultdict
from typing import Callable, Dict

from spectra_lexer.utils import recurse


class AbstractMod:

    @classmethod
    def subclasses(cls) -> set:
        """ Recursively gather all unique descendents of <cls>, excluding itself. """
        return set(recurse(cls, iter_fn=type.__subclasses__)) - {cls}


class MainMod(AbstractMod):
    """ Each main component mod has a named key. This makes them directly usable in any component class body. """

    KEY: str

    @classmethod
    def classes(cls) -> Dict[str, AbstractMod]:
        return {subcls.KEY: subcls for subcls in cls.subclasses()}


class ComponentMod(AbstractMod):
    """ The golden rule of component mods is that the code must operate as normal even without engine support.
        To that end, they must replace anything they decorate with either the original value or a default.
        If any functions are permanently modified, pickling will fail, and so will multiprocessing. """

    _INSTANCES: dict = defaultdict(list)  # Class-specific dict of instances keyed by owner component class.
    _SENTINEL: object = object()          # Sentinel value to ensure that each mod cleans up after itself.

    _value: object = _SENTINEL  # The "original" value of what was modified, returned to its place after setup.
    _attr: str = None           # The attribute name assigned to this mod on the component class.

    def __init_subclass__(cls):
        """ Add a data dict with component classes as keys and lists of mod instances as values. """
        cls._INSTANCES = defaultdict(list)

    def __call__(self, func:Callable):
        """ When used as a decorator, the value will be the function, replaced on __set_name__. """
        self._value = func
        return self

    def __set_name__(self, owner:type, name:str) -> None:
        """ Add the instance to the class data dict, save the attribute name, and put the original value back.
            If the original value was a descriptor itself (or another mod), chain the __set_name__ call to it. """
        self._INSTANCES[owner].append(self)
        self._attr = name
        v = self._value
        if v is self._SENTINEL:
            raise TypeError("Component mod must define a value to replace itself.")
        setattr(owner, name, v)
        if hasattr(v, "__set_name__"):
            v.__set_name__(owner, name)

    @classmethod
    def lookup(cls, cmp:object) -> list:
        """ Return each mod of type <cls> from <cmp>'s class hierarchy. """
        return [m for subcls in type(cmp).__mro__ for m in cls._INSTANCES[subcls]]

    @classmethod
    def lookup_cmp_mods(cls, cmp:object) -> list:
        """ Return each mod descended from <cls> in <cmp>'s class hierarchy. """
        return [m for subcls in cls.subclasses() for m in subcls.lookup(cmp)]

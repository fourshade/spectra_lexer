from collections import defaultdict
from typing import Callable, Iterator, List


class ComponentModMeta(type):

    _CLASSES: dict = {}
    _dict: dict

    def __new__(mcs, name, bases, dct, key=None):
        """ Add a data dict with component classes as keys and lists of command instances as values.
            Register each subclass under a keyword if one is given. """
        cls = super().__new__(mcs, name, bases, dct)
        if key is not None:
            mcs._CLASSES[key or name] = cls
        cls._dict = defaultdict(list)
        return cls

    @classmethod
    def get_classes_by_key(mcs) -> dict:
        return mcs._CLASSES

    def lookup_by_owner(cls, owner:type) -> Iterator:
        """ Yield each mod of type <cls> or subclasses from the owner's class hierarchy. """
        for tp in owner.__mro__:
            for m in cls._dict[tp]:
                yield m

    def lookup_owners(cls) -> List[type]:
        """ Return every owner class with at least one mod of type <cls> or subclasses in its inheritance line. """
        return list(cls._dict)

    def lookup_mods(cls) -> list:
        """ Return all mods of type <cls> or subclasses. """
        return [m for v in cls._dict.values() for m in v]

    def register(cls, owner, self):
        for tp in cls.__mro__:
            if issubclass(tp, ComponentMod):
                tp._dict[owner].append(self)


class ComponentMod(metaclass=ComponentModMeta):
    """ The golden rule of component mods is that the code must operate as normal even without engine support.
        To that end, they must replace anything they decorate with either the original value or a default.
        If any functions are permanently modified, pickling will fail, and so will multiprocessing. """

    _attr: str = None              # The attribute name assigned to this mod on the component class.
    _value = _SENTINEL = object()  # The "original" value of what was modified, returned to its place after setup.

    def __call__(self, func:Callable):
        """ When used as a decorator, the value will be the function, replaced on __set_name__. """
        self._value = func
        return self

    def __set_name__(self, owner:type, name:str) -> None:
        """ Add the owner class hierarchy to the data dict, save the attribute name, and put the original value back.
            If the original value was a descriptor itself (or another mod), chain the __set_name__ call to it. """
        self.__class__.register(owner, self)
        self._attr = name
        v = self._value
        if v is self._SENTINEL:
            raise TypeError("Component mod must define a value to replace itself.")
        setattr(owner, name, v)
        if hasattr(v, "__set_name__"):
            v.__set_name__(owner, name)

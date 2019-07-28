""" Contains engine command decorators and derivatives. """

from collections import defaultdict
from functools import partial, update_wrapper
from typing import Callable, Hashable, Iterator, List, Tuple


class Command:
    """ A basic command that binds to a component upon engine construction. """

    _INSTANCES: dict = defaultdict(list)  # Dict of command instances keyed by owner component class.

    def __init__(self, fn:Callable):
        """ Wrap the command with the attribute name assigned to this function as well as other details. """
        update_wrapper(self, fn)

    def __call__(self, *args, **kwargs):
        """ This can only be called if a component is not bound (i.e. during unit tests).
            In those cases, the methods under test are manually bound. The rest should do nothing. """

    def __set_name__(self, owner:type, name:str) -> None:
        """ Add the instance to the class data dicts. """
        self._INSTANCES[owner].append(self)

    @classmethod
    def bind_all(cls, cmp:object, call:Callable) -> List[Tuple[Hashable, Callable]]:
        """ Bind a component to mods from its class hierarchy and return the commands. """
        cmp.engine_call = call
        return [(m, func) for subcls in type(cmp).__mro__ for m in cls._INSTANCES[subcls] for func in m.bind(cmp)]

    def bind(self, cmp:object) -> Iterator[Callable]:
        """ Bind the component instance to execute the method on command call, if it implements it.
            If it does not implement it, replace it with an engine call to components that do. """
        attr = self.__name__
        if getattr(cmp.__class__, attr) is self:
            setattr(cmp, attr, self.wrap(cmp))
        else:
            yield getattr(cmp, attr)

    class call_wrapper(partial):
        def __repr__(self) -> str:
            return f"<COMMAND: {self.args[0].__name__}>"

    def wrap(self, instance:object):
        wrapper = self.call_wrapper(instance.engine_call, self)
        return update_wrapper(wrapper, self)


class CommandGroup:
    """ Group of engine commands declared by component classes. """

    _cmds: list

    def __init__(self):
        self._cmds = []

    def __call__(self, fn:Callable) -> Command:
        cmd = Command(fn)
        self._cmds.append(cmd)
        return cmd

    def __get__(self, instance:object, owner:type=None) -> List[Callable]:
        """ Bind the commands to any component that accesses this so it can call them. """
        return [cmd.wrap(instance) for cmd in self._cmds]

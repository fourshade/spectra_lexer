""" Contains engine command decorators and derivatives. """

from collections import defaultdict
from functools import partial, update_wrapper
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Tuple


class AbstractCommand:

    _INSTANCES: dict = defaultdict(list)  # Dict of command instances keyed by owner component class.

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
        """ Bind a component instance to execute a method on command call. """
        raise NotImplementedError

    class call_wrapper(partial):
        def __repr__(self) -> str:
            return f"<COMMAND: {self.args[0].__name__}>"

    def wrap(self, instance:object):
        wrapper = self.call_wrapper(instance.engine_call, self)
        return update_wrapper(wrapper, self)


class Command(AbstractCommand):
    """ A basic command that binds to a component upon engine construction. """

    def __init__(self, fn:Callable):
        """ Wrap the command with the attribute name assigned to this function as well as other details. """
        update_wrapper(self, fn)

    def bind(self, cmp:object) -> Iterator[Callable]:
        """ Bind the component instance to execute the method on command call, if it implements it.
            If it does not implement it, replace it with an engine call to components that do. """
        attr = self.__name__
        if getattr(cmp.__class__, attr) is self:
            setattr(cmp, attr, self.wrap(cmp))
        else:
            yield getattr(cmp, attr)


class CommandGroup:
    """ Group of engine commands declared by component classes. """

    def __init__(self):
        self._cmds: list = []

    def __call__(self, fn:Callable) -> Command:
        cmd = Command(fn)
        self._cmds.append(cmd)
        return cmd

    def __get__(self, instance:object, owner:type) -> List[Callable]:
        """ Bind the commands to any component that accesses this so it can call them. """
        return [cmd.wrap(instance) for cmd in self._cmds]


class Resource(AbstractCommand):
    """ An external resource that stores its value on the component. """

    default: Any
    _rs_attr: str

    def __init__(self, default:Any=None):
        self.default = default
        self._rs_attr = f"RS_{id(self)}"

    def __get__(self, instance:object, owner:type) -> Any:
        return getattr(instance, self._rs_attr, self.default)

    def bind(self, cmp:object) -> Iterator[Callable]:
        """ Store the provided value on command call. """
        yield partial(setattr, cmp, self._rs_attr)

    def __set__(self, instance:object, value) -> None:
        """ Call the engine to set the resource. Set our own attribute during non-connected tests. """
        try:
            self.wrap(instance)(value)
        except AttributeError:
            next(self.bind(instance))(value)

    def __set_name__(self, owner:type, name:str) -> None:
        """ Resources bound directly to names should use those names. """
        super().__set_name__(owner, name)
        self._rs_attr = f"RS_{name}"


class OptionGroup:
    """ Group of option resources declared by component classes. """

    def __init__(self):
        self._options: dict = {}

    def __call__(self, *keys:str, default:Any=None, desc:str="") -> Resource:
        rs = Resource(default)
        rs.desc = desc
        self._options[keys] = rs
        return rs

    def __get__(self, instance:object, owner:type) -> List[tuple]:
        return [(*keys, opt.default, opt.desc) for keys, opt in self._options.items()]

    def __set__(self, instance:object, value:Iterable[tuple]) -> None:
        """ Update all options by setting descriptors manually. """
        for *keys, val in value:
            opt = self._options.get(tuple(keys))
            if opt is not None:
                opt.__set__(instance, val)

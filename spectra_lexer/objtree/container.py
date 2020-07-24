""" Module for data providers that access objects contained within other objects. """

import builtins
import dis
import io
import types
from types import CodeType, FrameType, FunctionType
from typing import AbstractSet, Any, Callable, Iterator, List, Mapping, MutableMapping, MutableSequence, MutableSet, \
    Sequence, Type, Hashable


class BaseContainer(Mapping):
    """ Base class for a provider of child objects from a 'container' of some type.
        The 'container' object may be iterable, have attributes, or have other data that can be presented as contents.
        No matter how the object is accessed, each container must present its contents as a mapping. """

    color = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip = value_tooltip = "Immutable structure; cannot edit."
    show_item_count = False  # If True, len of items will be added to the base object's data.

    def __init__(self, obj:Any) -> None:
        self._obj = obj  # Object to be analyzed as a container (of some sort).

    def __iter__(self) -> Iterator:
        """ Some objects could have thousands of items or even iterate indefinitely.
            To be safe, only use lazy iterators so the program can stop evaluation at a defined limit. """
        return iter(self._obj)

    def __len__(self) -> int:
        """ Only sized containers are currently supported. """
        return len(self._obj)

    def __getitem__(self, key:Any) -> Any:
        """ Whatever contents we have, they must be keyed in some way to satisfy the mapping protocol.
            Most containers can be subscripted. Ones that can't must have an alternate way to find items by key. """
        return self._obj[key]

    key_str = str  # Return the key display value. It is just str(key) by default; subclasses may override this.


class MutableContainer(BaseContainer, MutableMapping):
    """ Base subclass for mutable containers. Mutation methods correspond to those used on mappings by default. """

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    def __delitem__(self, key:Any) -> None:
        del self._obj[key]

    def __setitem__(self, key:Any, value:Any) -> None:
        self._obj[key] = value


class MovableKeyContainer(MutableContainer):
    """ Base subclass for mutable containers where it makes sense to change an item's order/key. """

    key_tooltip = "Double-click to move this item to another key."

    def moveitem(self, old_key:Any, new_key:Any) -> None:
        """ Move an item from one key to another. """
        self[new_key] = self[old_key]
        del self[old_key]


class GeneratedContainer(BaseContainer):
    """ Base subclass for an immutable container that generates a dict from the original object and reads from that. """

    color = (32, 32, 128)  # Auto-generated containers are blue.
    key_tooltip = value_tooltip = "Auto-generated item; cannot edit."

    def __init__(self, obj:Any) -> None:
        d = self._gen_dict(obj)
        super().__init__(d)

    def _gen_dict(self, obj:Any) -> dict:
        """ Generate a dict that will be used directly as the mapping of container contents. Should be overridden. """
        return {}


class ContainerRegistry:
    """ Tracks container access classes by their conditions for use. """

    # Default data types to treat as atomic/indivisible. Attempting iteration on these is either wasteful or harmful.
    # Strings are the primary use case; expanding strings into characters is not useful and just makes a mess.
    # (especially since each character is a string containing *itself*, leading to infinite recursion.)
    ATOMIC_TYPES = {type(None), type(...),      # System singletons.
                    bool, int, float, complex,  # Guaranteed not iterable.
                    str, bytes, bytearray,      # Items are just characters; do not iterate over these.
                    range, slice,               # Items are just a pre-determined mathematical range.
                    filter, map, zip,           # Iteration is destructive.
                    io.TextIOWrapper}           # Iteration over a blocking input stream may hang the program.

    class Condition:
        """ A container access condition, tested against some property of an object. """
        def __init__(self, cmp_func:Callable[[object, object], bool], prop:object) -> None:
            """ The decorated class is only instantiated if cmp_func(<test object>, prop) is True. """
            self.cls = None
            self.cmp_func = cmp_func
            self.prop = prop
        def __call__(self, cls:Type[BaseContainer]) -> Type[BaseContainer]:
            self.cls = cls
            return cls

    def __init__(self, atomic_types=frozenset(ATOMIC_TYPES)) -> None:
        self._atomic_types = atomic_types  # Data types which are prevented from acting like containers.
        self._conditions = []              # List of use conditions for various classes.

    def containers_from(self, obj:object) -> List[BaseContainer]:
        """ Return container accessors that pass condition checks against <obj>. """
        if type(obj) in self._atomic_types:
            return []
        # If an class's use condition is met, that class will be instantiated and may provide data from the object.
        classes = [cond.cls for cond in self._conditions if cond.cmp_func(obj, cond.prop)]
        # If any classes are in a direct inheritance line, only instantiate the most derived class.
        return [cls(obj) for cls in classes if cls and sum([issubclass(m, cls) for m in classes]) == 1]

    def register(self, cmp_func:Callable, prop:object) -> Callable:
        """ Decorator to register a new condition for a container access class. These may be nested. """
        cond = self.Condition(cmp_func, prop)
        self._conditions.append(cond)
        return cond


# Every container below must be registered to be found by the data factory.
CONTAINER_TYPES = ContainerRegistry()


@CONTAINER_TYPES.register(isinstance, Mapping)
class UnorderedContainer(BaseContainer):
    """ A sized, unordered iterable item container. The most generic acceptable type of iterable container.
        Items may be sorted for display if they are orderable. Mappings do not need a subclass beyond this. """

    _AUTOSORT_MAXSIZE = 200
    show_item_count = True

    def __iter__(self) -> Iterator:
        """ If the container is under a certain size, attempt to sort its objects by key.
            A sort operation may fail if some keys aren't comparable. """
        if len(self) < self._AUTOSORT_MAXSIZE:
            try:
                return iter(sorted(self._obj))
            except TypeError:
                pass
        return iter(self._obj)


@CONTAINER_TYPES.register(isinstance, MutableMapping)
class MutableMappingContainer(UnorderedContainer, MovableKeyContainer):
    """ The base mutable container class is already implemented as a mapping. No changes need to be made. """


@CONTAINER_TYPES.register(isinstance, AbstractSet)
class SetContainer(UnorderedContainer):

    key_tooltip = "Hash value of the object. Cannot be edited."

    def __getitem__(self, key:Hashable) -> Any:
        """ Each object is its own key. This is really the only way to 'index' a set. """
        if key in self._obj:
            return key
        raise KeyError(key)

    def key_str(self, key:Hashable) -> str:
        """ Since objects behave as both the keys and the values, display hashes in the key field. """
        return f"#{hash(key)}"


@CONTAINER_TYPES.register(isinstance, MutableSet)
class MutableSetContainer(SetContainer, MutableContainer):

    def __delitem__(self, key:Hashable) -> None:
        """ The key is the old object itself. Remove it. """
        self._obj.discard(key)

    def __setitem__(self, key:Hashable, value:Any) -> None:
        """ The key is the old object itself. Remove it and add the new object. """
        del self[key]
        self._obj.add(value)


@CONTAINER_TYPES.register(isinstance, Sequence)
class SequenceContainer(BaseContainer):

    show_item_count = True

    def __iter__(self) -> Iterator[int]:
        """ Generate sequential index numbers as the keys. """
        return iter(range(len(self._obj)))

    def key_str(self, key:int) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"


@CONTAINER_TYPES.register(isinstance, tuple)
class TupleContainer(SequenceContainer):

    def key_str(self, key:int) -> str:
        """ By default, namedtuples display as regular tuples. Show them with their named fields instead. """
        if hasattr(self._obj, "_fields"):
            return f".{key} - {self._obj._fields[key]}"
        return super().key_str(key)


@CONTAINER_TYPES.register(isinstance, MutableSequence)
class MutableSequenceContainer(SequenceContainer, MovableKeyContainer):

    key_tooltip = "Double-click to move this item to a new index (non-negative integers only)."

    def moveitem(self, old_key:int, new_key:str) -> None:
        """ Moving a sequence item from one index to another can be done, but it will shift every item in between. """
        k = int(new_key)
        self[k:k] = [self[old_key]]
        del self[old_key + (old_key >= k)]


@CONTAINER_TYPES.register(hasattr, "__dict__")
class AttrContainer(MovableKeyContainer):
    """ A container that displays (and edits) the contents of an object's attribute dict. """

    key_tooltip = "Double-click to change this attribute name."
    value_tooltip = "Double-click to edit this attribute value."

    def __iter__(self) -> Iterator[str]:
        return iter(vars(self._obj))

    def __len__(self) -> int:
        return len(vars(self._obj))

    def __getitem__(self, key:str) -> Any:
        """ Return the attribute under <key> by any method we can. """
        try:
            return vars(self._obj)[key]
        except KeyError:
            return getattr(self._obj, key)

    def __delitem__(self, key:str) -> None:
        """ Delete the attribute under <key> if it exists. """
        if hasattr(self._obj, key):
            delattr(self._obj, key)

    def __setitem__(self, key:str, value:Any) -> None:
        """ __dict__ may be a mappingproxy, so setattr is the best way to set attributes.
            Deleting the attribute before setting the new value may help to override data descriptors. """
        del self[key]
        setattr(self._obj, key, value)


@CONTAINER_TYPES.register(hasattr, "__dict__")
class ClassContainer(GeneratedContainer):
    """ A container that displays the class hierarchy for instances of user-defined classes.
        Built-in types are excluded; they provide next to nothing useful in their attr listings.
        (an especially pathological case is type, which is an instance of *itself*.) """

    _EXCLUDED_CLASSES = {x for module in [builtins, types] for x in vars(module).values() if isinstance(x, type)}

    def _gen_dict(self, obj:Any) -> dict:
        """ Add each valid parent class as a container item. """
        return {cls.__name__: cls for cls in type(obj).__mro__ if cls not in self._EXCLUDED_CLASSES}


@CONTAINER_TYPES.register(hasattr, "__func__")
class WrapperContainer(GeneratedContainer):
    """ A container that exposes the contents of function wrappers. """

    def _gen_dict(self, obj:Any) -> dict:
        """ Also expose targets of bound methods. Suppress any attributes set to None. """
        d = {}
        for k in ("__self__", "__func__"):
            v = getattr(obj, k, None)
            if v is not None:
                d[k] = v
        return d


@CONTAINER_TYPES.register(isinstance, BaseException)
class ExceptionContainer(GeneratedContainer):
    """ A container for an exception object to show details about the entire stack. """

    def _gen_dict(self, exc:BaseException) -> dict:
        """ Add all arguments, then parent exceptions (cause/context), then each frame object going down the stack. """
        d = {f'arg{i}': v for i, v in enumerate(exc.args)}
        for k in ("__cause__", "__context__"):
            v = getattr(exc, k)
            if v is not None:
                d[k] = v
        tb = exc.__traceback__
        while tb is not None:
            f = tb.tb_frame
            d[f'{f.f_code.co_name}:{tb.tb_lineno}'] = f
            tb = tb.tb_next
        return d


@CONTAINER_TYPES.register(isinstance, FrameType)
class FrameContainer(GeneratedContainer):
    """ Shows inspectable information about a stack frame. """

    def _gen_dict(self, f:FrameType) -> dict:
        """ Add only the most usable information. """
        code = f.f_code
        return {"name": code.co_name, "filename": code.co_filename, "lineno": f.f_lineno,
                "globals": f.f_globals, "locals": f.f_locals, "code": code}


class instruction:
    """ A bytecode instruction as displayed in the debug tree. Has a special icon. """

    __slots__ = ["_instr"]

    def __init__(self, instr:dis.Instruction) -> None:
        self._instr = instr

    def __repr__(self) -> str:
        """ Show the instruction's argument (if any) as a string. """
        instr = self._instr
        if instr.arg is None:
            return ""
        elif not instr.argrepr:
            return f'{instr.arg}'
        else:
            return f'{instr.arg} ({instr.argrepr})'


@CONTAINER_TYPES.register(isinstance, (FunctionType, CodeType))
class CodeContainer(GeneratedContainer):
    """ Shows disassembly of a code object. """

    def _gen_dict(self, obj:Any) -> dict:
        """ To display bytecode properly in the tree, make a special display object for each instruction found.
            If an instruction has a code object as its argument, add that instead. """
        d = {}
        for instr in dis.get_instructions(obj):
            k = f'{instr.offset} {instr.opname}'
            if hasattr(instr.argval, 'co_code'):
                v = instr.argval
            else:
                v = instruction(instr)
            d[k] = v
        return d

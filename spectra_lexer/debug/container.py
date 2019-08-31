""" Module for data providers that access objects contained within other objects. """

import builtins
import dis
from functools import partial
import types
from types import CodeType, FrameType, FunctionType, MethodType
from typing import AbstractSet, Any, Callable, Iterator, List, Mapping, MutableMapping, MutableSequence, MutableSet, \
    Sequence, Type, Union, Hashable

from .data import DebugData
from .resource import AutoImporter


class BaseContainer(Mapping):
    """ Base class for a provider of child objects from a 'container' of some type.
        The 'container' object may be iterable, have attributes, or have other data that can be presented as contents.
        No matter how the object is accessed, each container must present its contents as a mapping. """

    color: tuple = (96, 64, 64)  # Immutable containers have a light color.
    key_tooltip: str = "Immutable structure; cannot edit."
    value_tooltip: str = key_tooltip
    show_item_count: bool = False  # If True, len of items will be added to the base object's data.

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

    def set_data(self, key:Any, data:DebugData) -> None:
        """ Add all base container data for the given key. This data usually has the lowest override priority.
            This data comes from properties of the *container* only, not the object inside. """
        data.color = self.color
        data.key_tooltip = self.key_tooltip
        data.key_text = self._key_str(key)
        data.value_tooltip = self.value_tooltip

    _key_str = str  # Return the key display value. It is just str(key) by default; subclasses should override this.


class MutableContainer(BaseContainer):
    """ Base subclass for mutable containers. Mutation methods correspond to those used on mappings by default. """

    color = (0, 0, 0)  # Mutable containers are the default color of black.
    key_tooltip = "This key may not be changed."
    value_tooltip = "Double-click to edit this value."

    _eval_ns: AutoImporter = None  # Namespace for evaluation of user input strings as Python code.

    def __delitem__(self, key:Any) -> None:
        del self._obj[key]

    def __setitem__(self, key:Any, value:Any) -> None:
        self._obj[key] = value

    def set_data(self, key:Any, data:DebugData) -> None:
        """ Include a callback for editing of values in the data dict with Python expressions. """
        super().set_data(key, data)
        data.value_edit = partial(self.eval_setitem, key)

    def eval_setitem(self, key:Any, user_input:str) -> None:
        """ Since only strings can be entered, we must evaluate them as Python expressions.
            ast.literal_eval is safer, but not quite as useful (or fun). No need for restraint here. """
        try:
            self[key] = self.eval(user_input)
        except Exception as e:
            # User input + eval = BREAK ALL THE THINGS!!! At least try to replace the item with the exception.
            self[key] = e

    @classmethod
    def eval(cls, user_input:str) -> Any:
        """ Only create the auto-import dict if someone tries to make a change. """
        if cls._eval_ns is None:
            cls._eval_ns = AutoImporter()
        return cls._eval_ns.eval(user_input)


class MovableKeyContainer(MutableContainer):
    """ Base subclass for mutable containers where it makes sense to change an item's order/key. """

    key_tooltip = "Double-click to move this item to another key."

    def moveitem(self, old_key:Any, new_key:str) -> None:
        """ Move an item from one key to another. """
        self[new_key] = self[old_key]
        del self[old_key]

    def set_data(self, key:Any, data:DebugData) -> None:
        """ Include a callback for editing of string keys in the data dict. """
        super().set_data(key, data)
        data.key_edit = partial(self.eval_moveitem, key)

    def eval_moveitem(self, key:Any, user_input:str) -> None:
        """ Only allow movement using literal string input for now. """
        self.moveitem(key, user_input)


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
    """ Tracks container classes by their conditions for use. """

    class Condition:
        """ Each container class is decorated with a condition which attempts to match some property of an object. """
        def __init__(self, cmp_func:Callable[[object, object], bool], prop:object) -> None:
            """ The class is only instantiated if cmp_func(<test object>, prop) is True. """
            self.cls = None
            self.cmp_func = cmp_func
            self.prop = prop
        def __call__(self, cls:Type[BaseContainer]) -> Type[BaseContainer]:
            self.cls = cls
            return cls

    def __init__(self) -> None:
        self._conditions = []  # List of classes together with their use conditions.

    def match(self, obj:object) -> List[BaseContainer]:
        """ Return container classes that match conditions on the object's properties.
            If a condition is met, that container class will be instantiated and may provide data from the object.
            If any container classes are in a direct inheritance line, only keep the most derived class. """
        classes = [cond.cls for cond in self._conditions if cond.cmp_func(obj, cond.prop)]
        return [cls(obj) for cls in classes if cls and sum([issubclass(m, cls) for m in classes]) == 1]

    def register(self, cmp_func:Callable, prop:object) -> Callable:
        """ Decorator to register a new condition for a container class. These may be nested. """
        cond = self.Condition(cmp_func, prop)
        self._conditions.append(cond)
        return cond


# Every container below must be registered to be found by the data factory.
CONTAINER_TYPES = ContainerRegistry()


@CONTAINER_TYPES.register(isinstance, Mapping)
class UnorderedContainer(BaseContainer):
    """ A sized, unordered iterable item container. The most generic acceptable type of iterable container.
        Items may be sorted for display if they are orderable. Mappings do not need a subclass beyond this. """

    _AUTOSORT_MAXSIZE: int = 200
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

    def _key_str(self, key:Hashable) -> str:
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

    def _key_str(self, key:int) -> str:
        """ Add a dot in front of each index for clarity. """
        return f".{key}"


@CONTAINER_TYPES.register(isinstance, tuple)
class TupleContainer(SequenceContainer):

    def _key_str(self, key:int) -> str:
        """ By default, namedtuples display as regular tuples. Show them with their named fields instead. """
        if hasattr(self._obj, "_fields"):
            return f".{key} - {self._obj._fields[key]}"
        return super()._key_str(key)


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

    key_tooltip: str = "Double-click to change this attribute name."
    value_tooltip: str = "Double-click to edit this attribute value."

    def __iter__(self) -> Iterator:
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
        The main exception is type, which is its own class and would expand indefinitely.
        Others include built-in types which provide next to nothing useful in their attr listings. """

    _EXCLUDED_CLASSES: set = {i for m in (builtins, types) for i in vars(m).values() if isinstance(i, type)}

    def _gen_dict(self, obj:Any) -> dict:
        """ Add each valid parent class as a child item. """
        return {cls.__name__: cls for cls in type(obj).__mro__ if cls not in self._EXCLUDED_CLASSES}


@CONTAINER_TYPES.register(isinstance, BaseException)
class ExceptionContainer(GeneratedContainer):
    """ A container for an exception object to show details about the entire stack. """

    def _gen_dict(self, exc:BaseException) -> dict:
        """ Add parent exceptions (cause/context), then each frame object going down the stack. """
        d = {f"arg{i}": v for i, v in enumerate(exc.args)}
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
    """ Shows all information about a stack frame. """

    def _gen_dict(self, f:FrameType) -> dict:
        """ Add only the most important inspectable information. """
        code = f.f_code
        return dict(name=code.co_name, filename=code.co_filename, lineno=f.f_lineno,
                    globals=f.f_globals, locals=f.f_locals, code=code)


class instruction:
    """ A bytecode instruction as displayed in the debug tree. Has a special icon. """

    __slots__ = ["_s"]

    def get(self, inst:dis.Instruction):
        """ Set an instruction's argument as a display string. If it is a code object, return that instead. """
        if hasattr(inst.argval, 'co_code'):
            return inst.argval
        if inst.arg is None:
            self._s = ""
        elif not inst.argrepr:
            self._s = f'{inst.arg}'
        else:
            self._s = f'{inst.arg} ({inst.argrepr})'
        return self

    def __repr__(self) -> str:
        return self._s


# Types known to consist of or contain inspectable bytecode.
_CODE_TYPES = (MethodType, FunctionType, CodeType, classmethod, staticmethod)


@CONTAINER_TYPES.register(isinstance, _CODE_TYPES)
class CodeContainer(GeneratedContainer):
    """ Shows disassembly of a code object. """

    def _gen_dict(self, obj:Union[_CODE_TYPES]) -> dict:
        """ To display bytecode properly in the tree, make a special display object for each instruction found. """
        return {f'{inst.offset} {inst.opname}': instruction().get(inst) for inst in dis.get_instructions(obj)}

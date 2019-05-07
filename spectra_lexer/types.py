""" --------------------------GENERAL PURPOSE CLASSES---------------------------
    These classes are used to modify the behavior of attributes and methods on other classes.
    Some are used like functions or other low-level constructs, so their names are all lowercase. """

from collections import deque
from functools import partialmethod
import operator

# A robust dummy object. Always returns itself through any chain of attribute lookups, subscriptions, and calls.
_DUMMY_METHODS = ["__getattr__", "__getitem__", "__call__"]
dummy = type("dummy", (), dict.fromkeys(_DUMMY_METHODS, lambda self, *a, **k: self))()


class StructMeta(type):
    def __new__(mcs, name, bases, dct, _fields:tuple=(), _args:str=None, _kwargs:str=None, **opt_fields):
        """ Initialize a new struct subclass with <_fields> as required instance attribute names.
            All fields are filled in __init__ as with namedtuple, but these fields are mutable.
            Fields may be filled by arguments in order positionally, or in any order by keyword.
            <_args> specifies a field to receive a list of extra positional arguments, if any.
            <_kwargs> specifies a field to receive a dict of extra keyword arguments, if any.
            Any remaining keywords to this method become optional fields with default values.
            If subclassing an existing struct, required fields are added to the right of those on
            the base class. Optional/variadic fields extend or override the base class as normal. """
        cls = super().__new__(mcs, name, bases, dct)
        base_req_fields = [f for b in bases for f in getattr(b, "_REQ_FIELDS", ())]
        cls._REQ_FIELDS = (*base_req_fields, *_fields)
        base_opt_fields = {f: v for b in bases for f, v in getattr(b, "_OPT_FIELDS", {}).items()}
        cls._OPT_FIELDS = {**base_opt_fields, **opt_fields}
        if _args is not None:
            cls._ARGS_FIELD = _args
        if _kwargs is not None:
            cls._KWARGS_FIELD = _kwargs
        return cls


class struct(dict, metaclass=StructMeta):
    """ A convenience class for a simple data structure with mutable named fields and variadic args.
        Fields are accessible by attribute or subscription. Starts out empty; must be subclassed to be useful.
        Iteration provides fields in the order: [*positional, *keyword, args_field, kwargs_field]. """

    _ARGS_FIELD: str = None
    _KWARGS_FIELD: str = None

    def __init__(self, *args, **kwargs):
        """ Fill all fields named at creation, in order if possible. """
        super().__init__()
        args = deque(args)
        self._set_fields(self._REQ_FIELDS, args, kwargs, raise_if_short=True)
        self.update(self._OPT_FIELDS)
        self._set_fields(self._OPT_FIELDS, args, kwargs)
        self._set_varargs(self._ARGS_FIELD, tuple(args))
        self._set_varargs(self._KWARGS_FIELD, kwargs)
        # Make all fields accessible as instance attributes.
        self.__dict__ = self

    def _set_fields(self, fields, args:deque, kwargs:dict, raise_if_short:bool=False) -> None:
        """ Set each field using matching keyword args first, then positional args in order. """
        for f in fields:
            if f in kwargs:
                # If present in kwargs, the keyword is popped and placed in the field.
                self[f] = kwargs.pop(f)
            elif args:
                # If there are positional args left, pop the next one and place it in the field.
                self[f] = args.popleft()
            elif raise_if_short:
                # Raise if we ran out of args before filling every required field.
                raise TypeError(f"Not enough arguments in struct initializer; needed {len(fields)}, got {len(self)}.")

    def _set_varargs(self, v_attr:str, v_args) -> None:
        """ Check and/or fill variadic spillover fields. """
        if v_attr is not None:
            self[v_attr] = v_args
        elif v_args:
            raise TypeError(f"Too many arguments in struct initializer; extra = {v_args}")


class argcollector:
    """ Abstract class that simply saves its arguments when created and adds to them every time it is called.
        Since decorator classes require an initialization followed by a call, it works well as a base for them. """

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        self.args += args
        self.kwargs.update(kwargs)
        return self.decorate(*self.args, **self.kwargs)

    def decorate(self, *args, **kwargs):
        """ Subclasses can decorate functions and classes here. The last positional arg will be the callable. """
        return self


class delegate_to(argcollector):
    """ Descriptor to delegate method calls on the assigned name to an instance member object.
        If there are dots in <attr>, method calls on self.<name> are redirected to self.<dotted.path.in.attr>.
        If there are no dots in <attr>, method calls on self.<name> are redirected to self.<attr>.<name>.
        Partial function arguments may also be added, though the performance cost is considerable.
        Some special methods may be called implicitly. For these, call the respective builtin or operator. """

    _BUILTINS = [bool, int, float, str, repr, format, iter, next, reversed, len, hash, dir, getattr, setattr, delattr]
    _SPECIAL_METHODS = {**vars(operator), **{f"__{fn.__name__}__": fn for fn in _BUILTINS}}

    def __set_name__(self, owner:type, name:str) -> None:
        attr, *partial_args = self.args
        partial_kwargs = self.kwargs
        special = self._SPECIAL_METHODS.get(name)
        if special is not None:
            def delegate(instance, *args, _call=special, _attr=attr, **kwargs):
                return _call(getattr(instance, _attr), *args, **kwargs)
        else:
            getter = operator.attrgetter(attr if "." in attr else f"{attr}.{name}")
            def delegate(instance, *args, _get=getter, **kwargs):
                return _get(instance)(*args, **kwargs)
        if partial_args or partial_kwargs:
            delegate = partialmethod(delegate, *partial_args, **partial_kwargs)
        setattr(owner, name, delegate)


class polymorph_index(dict):
    """ Class decorator for recording polymorphic subtypes in a dict by key. """

    def __call__(self, key):
        def recorder(fn):
            self[key] = fn
            return fn
        return recorder

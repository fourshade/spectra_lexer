""" --------------------------GENERAL PURPOSE CLASSES---------------------------
    These classes are used to modify the behavior of attributes and methods on other classes.
    Some are used like functions or other low-level constructs, so their names are all lowercase. """

from functools import partialmethod
import operator

# A robust dummy object. Always returns itself through any chain of attribute lookups, subscriptions, and calls.
_DUMMY_METHODS = ["__getattr__", "__getitem__", "__call__"]
dummy = type("dummy", (), dict.fromkeys(_DUMMY_METHODS, lambda self, *a, **k: self))()


class delegate_to:
    """ Descriptor to delegate method calls on the assigned name to an instance member object.
        If there are dots in <attr>, method calls on self.<name> are redirected to self.<dotted.path.in.attr>.
        If there are no dots in <attr>, method calls on self.<name> are redirected to self.<attr>.<name>.
        Partial function arguments may also be added, though the performance cost is considerable.
        Some special methods may be called implicitly. For these, call the respective builtin or operator. """

    _BUILTINS = [bool, int, float, str, repr, format, iter, next, reversed, len, hash, dir, getattr, setattr, delattr]
    _SPECIAL_METHODS = {**vars(operator), **{f"__{fn.__name__}__": fn for fn in _BUILTINS}}

    _params: tuple  # Contains the attribute name at minimum, with optional partial arguments.

    def __init__(self, attr, *partial_args, **partial_kwargs):
        self._params = attr, partial_args, partial_kwargs

    def __set_name__(self, owner:type, name:str) -> None:
        attr, partial_args, partial_kwargs = self._params
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


class prefix_index(polymorph_index):
    """ Class decorator for recording subtypes corresponding to a prefix of a string key. """

    def default(self):
        """ Set a default class, which is chosen if no other prefixes match. """
        return self("")

    def find(self, key:str) -> tuple:
        """ Try prefixes in order from longest to shortest. Return the prefix and class if we find a valid one. """
        for prefix in sorted(self, key=len, reverse=True):
            if key.startswith(prefix):
                return key[len(prefix):], self[prefix]

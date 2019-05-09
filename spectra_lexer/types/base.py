""" --------------------------GENERAL PURPOSE CLASSES---------------------------
    These classes are used to modify the behavior of attributes and methods on other classes.
    Some are used like functions or other low-level constructs, so their names are all lowercase. """

from functools import partialmethod
import operator

# A robust dummy object. Always returns itself through any chain of attribute lookups, subscriptions, and calls.
_DUMMY_METHODS = ["__getattr__", "__getitem__", "__call__"]
dummy = type("dummy", (), dict.fromkeys(_DUMMY_METHODS, lambda self, *a, **k: self))()


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

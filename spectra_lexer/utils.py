""" Module for generic utility functions that could be useful in many applications.
    Most are ruthlessly optimized, with attribute lookups and globals cached in default arguments. """

import ast
import functools
import inspect
import operator


# ---------------------------PURE UTILITY FUNCTIONS---------------------------

def nop(*args, **kwargs) -> None:
    """ ... """


def compose(*funcs):
    """ Compose a series of n callables to create a single callable that combines
        their effects, calling each one in turn with the result of the previous.
        The order is defined such that the first callable in the sequence receives
        the original arguments, i.e. compose(h, g, f)(*args) evaluates to f(g(h(*args))). """
    # Degenerate case: composition of 0 functions = identity function (single argument only).
    if not funcs:
        return lambda x: x
    # Feed the arguments to the first function and chain from there.
    f_first, *f_rest = funcs
    def composed(*args, **kwargs):
        result = f_first(*args, **kwargs)
        for f in f_rest:
            result = f(result)
        return result
    return composed


def traverse(obj:object, next_attr:str="next", sentinel:object=None):
    """ Traverse a linked-list type structure, following a chain of attribute references
        and yielding values until either the sentinel is found or the attribute is not.
        Reference loops will cause the generator to yield items forever. """
    while obj is not sentinel:
        yield obj
        obj = getattr(obj, next_attr, sentinel)


def recurse(obj:object, iter_attr:str=None, sentinel:object=None):
    """ Starting with a container object that can contain other similar container objects,
        yield that object, then recursively yield objects from its contents, depth-first.
        If iter_attr is None, the object must be an iterable container itself.
        If iter_attr is defined, it is the name of an iterable attribute.
        Recursion stops if the sentinel is encountered or the attribute is not found.
        Reference loops will cause the generator to recurse up to the recursion limit. """
    yield obj
    if iter_attr is not None:
        obj = getattr(obj, iter_attr, sentinel)
    if obj is not sentinel:
        for item in obj:
            yield from recurse(item, iter_attr, sentinel)


def merge(d_iter) -> dict:
    """ Merge all items in an iterable of mappings or other (k, v) item containers into a single dict. """
    merged = {}
    merged_update = merged.update
    for d in d_iter:
        merged_update(d)
    return merged


def ensure_list(obj:object) -> list:
    # Ensure the output object is a list by wrapping the object in a list if it isn't one already.
    return obj if isinstance(obj, list) else [obj]


# These functions ought to have been string built-ins. Pure Python string manipulation is slow as fuck.
# Even after caching attributes and globals, repeated string creation and function call overhead will eat you alive.

def _remove_char(s:str, c:str, _replace=str.replace) -> str:
    """ Return a copy of <s> with the character <c> removed starting from the left. """
    return _replace(s, c, "", 1)


def str_without(s:str, chars, _reduce=functools.reduce) -> str:
    """ Return <s> with each of the characters in <chars> removed, starting from the left. """
    # Fast path: if the characters are a direct prefix, just cut it off.
    prefix_length = len(chars)
    if s[:prefix_length] == chars:
        return s[prefix_length:]
    # Otherwise, each key must be removed individually.
    return _reduce(_remove_char, chars, s)


def str_prefix(s:str, sep:str=" ", _split=str.split) -> str:
    """ Return <s> from the start up to the first instance of <sep>. If <sep> is not present, return all of <s>. """
    return _split(s, sep, 1)[0]


def str_suffix(s:str, sep:str=" ", _split=str.split) -> str:
    """ Return <s> from the end up to the last instance of <sep>. If <sep> is not present, return all of <s>. """
    return _split(s, sep, 1)[-1]


def str_eval(val:str, _eval=ast.literal_eval) -> object:
    """ Try to convert a Python string to an object using AST. This fixes ambiguities such as bool('False') = True.
        Strings that are read as names will throw an error, in which case they should be returned as-is. """
    try:
        return _eval(val)
    except (SyntaxError, ValueError):
        return val


# ------------------------DECORATORS/NESTED FUNCTIONS-------------------------

def save_kwargs(fn):
    """ Decorator to save and re-use keyword arguments from previous calls to a function. """
    @functools.wraps(fn)
    def call(*args, _fn=fn, _saved_kwargs={}, **kwargs):
        _saved_kwargs.update(kwargs)
        return _fn(*args, **_saved_kwargs)
    return call


def with_sets(cls:type) -> type:
    """ Decorator for a constants class to add sets of all legal keys and values for membership testing. """
    cls.keys, cls.values = map(set, zip(*vars(cls).items()))
    return cls


def memodict(fn):
    """ The fastest possible method of memoizing a function with one hashable positional argument. """
    class MemoDict(dict):
        def __missing__(self, key:str, _fn=fn):
            ret = self[key] = _fn(key)
            return ret
    return MemoDict()


def memoize(fn, *, arg_count=None):
    """ Memoize a function using the best method possible for unlimited size.
        The number of positional args may be explicitly passed, or determined from the signature. """
    if arg_count is None:
        for f_obj in (fn, fn.__call__):
            try:
                params = inspect.signature(f_obj).parameters
            except (TypeError, ValueError):
                continue
            valid_kinds = {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
            if all(p.kind in valid_kinds for p in params.values()):
                arg_count = len(params)
                break
    if arg_count == 1:
        return memodict(fn).__getitem__
    # lru_cache is a good fallback for any case not handled above.
    return functools.lru_cache(maxsize=None)(fn)


# --------------------------GENERAL PURPOSE CLASSES---------------------------
# These classes are used to modify the behavior of attributes and methods on other classes.
# They are used like functions, so their names are all lowercase.

class _dummy:
    """ The ultimate dummy object. Always. Returns. Itself. """
    def __call__(self, *args, **kwargs): return self
    __getattr__ = __getitem__ = __call__
dummy = _dummy()


class delegate_to:
    """ Descriptor to delegate method calls on the assigned name to an instance member.
        If there are dots in <attr>, method calls on self.<name> are redirected to self.<dotted.path.in.attr>.
        If there are no dots in <attr>, method calls on self.<name> are redirected to self.<attr>.<name>.
        Partial function arguments may also be added, though the performance cost is considerable. """
    def __init__(self, attr:str, *partial_args, **partial_kwargs):
        self.params = attr, partial_args, partial_kwargs
    def __get__(self, instance:object, owner:type):
        return self.getter(instance)
    def __set_name__(self, owner:type, name:str) -> None:
        attr, partial_args, partial_kwargs = self.params
        getter = operator.attrgetter(attr if "." in attr else ".".join([attr, name]))
        if partial_args or partial_kwargs:
            def getter(instance:object, _agetter=getter, p_args=partial_args, p_kwargs=partial_kwargs):
                def p_call(*args, _func=_agetter(instance), **kwargs):
                    return _func(*p_args, *args, **p_kwargs, **kwargs)
                return p_call
        self.getter = getter

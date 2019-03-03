"""
Module for generic utility functions that could be useful in many applications.
Most are ruthlessly optimized, with attribute lookups and globals cached in default arguments.
"""

import ast
import functools


def nop(*args, **kwargs) -> None:
    """ ... """


def compose(*funcs:callable) -> callable:
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


def memoize_one_arg(fn:callable) -> callable:
    """ Decorator for the fastest possible method of memoizing a function with one hashable argument. """
    class MemoDict(dict):
        def __missing__(self, key):
            ret = self[key] = fn(key)
            return ret
    return MemoDict().__getitem__


def nondata_property(fn:callable) -> callable:
    """ Non-data descriptor version of a property. Instances can override this in their dictionary. """
    class NondataProp:
        def __get__(self, instance, owner) -> str:
            return fn(instance)
    return NondataProp()


def with_sets(cls:type) -> type:
    """ Decorator for a constants class to add sets of all legal keys and values for membership testing. """
    cls.keys, cls.values = map(set, zip(*vars(cls).items()))
    return cls


# These functions ought to have been string built-ins. Pure Python string manipulation is slow as fuck.
# Even after caching attributes and globals, repeated string creation and function call overhead will eat you alive.

def _remove_char(s:str, c:str, _replace=str.replace) -> str:
    """ Return a copy of <s> with the character <c> removed starting from the left. """
    return _replace(s, c, "", 1)


def str_without(s:str, chars:str, _reduce=functools.reduce) -> str:
    """ Return <s> with each of the characters in <chars> removed, starting from the left. """
    return _reduce(_remove_char, chars, s)


def str_prefix(s:str, sep:str=" ", _split=str.split) -> str:
    """ Return <s> from the start up to the first instance of <sep>. If <sep> is not present, return all of <s>. """
    return _split(s, sep, 1)[0]


def str_suffix(s:str, sep:str=" ", _split=str.split) -> str:
    """ Return <s> from the end up to the last instance of <sep>. If <sep> is not present, return all of <s>. """
    return _split(s, sep, 1)[-1]


def str_map(s:str, fn:callable, sep:str=" ", _split=str.split, _map=map, _join=str.join) -> str:
    """ Split the string on a delimiter, then map a str->str function to each piece and join it back together. """
    return _join(sep, _map(fn, _split(s, sep)))


def str_eval(val:str, _eval=ast.literal_eval) -> object:
    """ Try to convert a Python string to an object using AST. This fixes ambiguities such as bool('False') = True.
        Strings that are read as names will throw an error, in which case they should be returned as-is. """
    try:
        return _eval(val)
    except (SyntaxError, ValueError):
        return val

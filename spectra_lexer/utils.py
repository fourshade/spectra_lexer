""" Module for generic utility functions that could be useful in many applications.
    Most are ruthlessly optimized, with attribute lookups and globals cached in default arguments. """

import ast
import collections
import functools
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


def recurse(obj:object, iter_fn=iter, max_level:int=-1):
    """ Starting with a container object that can contain other similar container objects,
        recursively yield objects from its contents, depth-first.
        <iter_fn> is the function that gets the iterable contents, defaulting to iter.
        Recursion stops if the object evaluates False or is not iterable.
        If <max_level> is not negative, it will also stop after that many levels.
        Reference loops will cause the generator to recurse up to the recursion limit. """
    if max_level:
        try:
            for item in iter_fn(obj):
                yield item
                if item:
                    yield from recurse(item, iter_fn, max_level - 1)
        except TypeError:
            return


def recurse_attr(obj:object, attr:str, max_level:int=-1):
    """ Recurse over objects that have contents in an iterable attribute. """
    return recurse(obj, operator.attrgetter(attr), max_level)


def merge(d_iter) -> dict:
    """ Merge all items in an iterable of mappings or other (k, v) item containers into a single dict. """
    merged = {}
    merged_update = merged.update
    for d in d_iter:
        merged_update(d)
    return merged


def ensure_iterable(obj:object, blacklist:tuple=(str,), empty:tuple=(None,)):
    # Ensure the output object is iterable by wrapping it in a list if it isn't.
    # Iteration may not be desired on some types (such as strings), so they may be blacklisted as "not iterable".
    # Some types (such as None) are used to indicate the absence of a value, and may return an empty iterable.
    if isinstance(obj, blacklist):
        return [obj]
    if isinstance(obj, collections.abc.Iterable):
        return obj
    if obj in empty:
        return ()
    return [obj]


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


def str_suffix(s:str, sep:str=" ", _rsplit=str.rsplit) -> str:
    """ Return <s> from the end up to the last instance of <sep>. If <sep> is not present, return all of <s>. """
    return _rsplit(s, sep, 1)[-1]


def str_eval(val:str, _eval=ast.literal_eval) -> object:
    """ Try to convert a string to a Python object using AST. This fixes ambiguities such as bool('False') = True.
        Strings that are read as names will throw an error, in which case they should be returned as-is. """
    try:
        return _eval(val)
    except (SyntaxError, ValueError):
        return val


# ------------------------DECORATORS/NESTED FUNCTIONS-------------------------

def with_sets(cls:type) -> type:
    """ Decorator for a constants class to add sets of all legal keys and values for membership testing. """
    cls.keys, cls.values = map(set, zip(*vars(cls).items()))
    return cls


def memoize(fn):
    """ Decorator to memoize a function using the fastest method possible for unlimited size.
        There used to be Python tricks for fast caching, but functools.lru_cache now has a C implementation.
        The unbounded (non-LRU) case outperforms any cache system written in pure Python now. """
    return functools.lru_cache(maxsize=None)(fn)

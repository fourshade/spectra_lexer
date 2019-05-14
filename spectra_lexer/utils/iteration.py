""" Utility module for iterables and iteration. """

import operator
from collections.abc import Container


def ensure_iterable(obj:object, *, blacklist:Container=(str,), empty:Container=(type(None),), iter_items:bool=True):
    """ Ensure an object is iterable by wrapping it in a list if it isn't. Also covers a few special cases:
        blacklist - Types to treat as "not iterable". Iteration over the characters of a string is usually unwanted.
            empty - Types used to indicate the absence of a value. Will return an empty iterable.
       iter_items - For a mapping, do we iterate over the items (True) or the keys (False)? """
    tp = type(obj)
    if tp in blacklist:
        return [obj]
    if tp in empty:
        return ()
    if hasattr(tp, "items") and iter_items:
        return obj.items()
    return obj if hasattr(tp, "__iter__") else [obj]


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
    yield obj
    if max_level:
        try:
            for item in iter_fn(obj):
                yield from recurse(item, iter_fn, max_level - 1)
        except TypeError:
            return


def recurse_attr(obj:object, attr:str, max_level:int=-1):
    """ Recurse over objects that have contents in an iterable attribute. """
    return recurse(obj, operator.attrgetter(attr), max_level)

""" Module for generic utility functions that could be useful in many applications. """

from typing import Callable, Generator, Iterable, List


def nop(*args, **kwargs) -> None:
    """ ... """


def compose(*funcs:Callable) -> Callable:
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


def traverse(obj:object, next_attr:str="next", sentinel:object=None) -> Generator:
    """ Traverse a linked-list type structure, following a chain of attribute references
        and yielding values until either the sentinel is found or the attribute is not.
        Reference loops will cause the generator to yield items forever. """
    while obj is not sentinel:
        yield obj
        obj = getattr(obj, next_attr, sentinel)


def recurse(obj, iter_attr:str=None, sentinel:object=None) -> Generator:
    """ Starting with a container object that can contain other objects of its own type,
        yield that object, then recursively yield objects from each of its children.
        If iter_attr is None, the object must be an iterable container itself.
        If iter_attr is defined, it is the name of an iterable attribute.
        Recursion stops if the sentinel is encountered or the attribute is not found.
        Reference loops will cause the generator to recurse up to the recursion limit. """
    yield obj
    if iter_attr is not None:
        obj = getattr(obj, iter_attr, sentinel)
    if obj is not sentinel:
        for item in obj:
            yield from recurse(item, iter_attr=iter_attr, sentinel=sentinel)


def merge(d_iter:Iterable[dict]) -> dict:
    """ Merge all items in an iterable of dicts. For duplicate keys, the last value takes precedence. """
    merged = {}
    for d in d_iter:
        merged.update(d)
    return merged


class Node:
    """ Generic class for an object that may contain other instances of its own type (i.e. a tree node).
        Each instance contains a list of zero or more children. Reference cycles are not allowed. """

    parent: __qualname__          # Direct parent of the node. If None, it is the root node (or unconnected).
    children: List[__qualname__]  # Direct children of the node. If empty, it is considered a leaf node.

    def __init__(self):
        self.parent = None
        self.children = []

    def __iter__(self) -> Generator:
        return recurse(self, iter_attr="children")

    def add_children(self, nodes:Iterable[__qualname__]) -> None:
        for n in nodes:
            n.parent = self
            self.children.append(n)

    def get_ancestors(self) -> List[__qualname__]:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return list(traverse(self, next_attr="parent"))

    def get_descendents(self) -> List[__qualname__]:
        """ Get a list of all descendents of this node (starting with itself) down to the base. """
        return list(self)

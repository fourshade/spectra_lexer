"""
Module for generic data structures used in the program.
Each one is usually subclassed for more specific purposes.
"""

from collections import defaultdict
from functools import reduce
from typing import List, Sequence, TypeVar

from spectra_lexer.utils import recurse, traverse


class Struct:
    """ A class whose sole purpose is to hold custom attributes. A bare object(), surprisingly, cannot do this.
        The counterpart to the nop() function in utils; stupidly simple yet occasionally useful. """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class PrefixTree(defaultdict):
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _ET = TypeVar("_ET")  # Key element type.
    _VT = TypeVar("_VT")  # Value type.

    def __init__(self):
        """ Self-referential defaultdict factory. Creates an indefinitely nested series of defaultdicts. """
        super().__init__(PrefixTree, val=[])

    def add(self, k:Sequence[_ET], v:_VT) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        reduce(dict.__getitem__, k, self)["val"].append(v)

    def match(self, k:Sequence[_ET]) -> List[_VT]:
        """ From a given sequence, return an iterable of all of the values that match
            any prefix of it in order from shortest prefix matched to longest. """
        node = self
        lst = node["val"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            lst += node["val"]
        return lst


class Node:
    """ Class representing a node in a tree structure with linear indexing.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child sequence may be mutable, hashing is by identity only. """

    parent = None            # Direct parent of the node. If None, it is the root node (or unconnected).
    children: Sequence = ()  # Direct children of the node. If empty, it is considered a leaf node.

    def __init__(self, nodes:Sequence=()):
        """ Set an optional sequence of nodes to be this node's children. """
        if nodes:
            for n in nodes:
                n.parent = self
            self.children = nodes

    def get_ancestors(self) -> list:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return list(traverse(self, next_attr="parent"))

    def get_descendents(self) -> list:
        """ Get a list of all descendents of this node (starting with itself) searching depth-first. """
        return list(recurse(self, iter_attr="children"))

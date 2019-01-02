"""
Module for generic data structures used in the program.
Each one is usually subclassed for more specific purposes.
"""

from collections import defaultdict
from functools import reduce
from typing import List, Sequence, TypeVar

from spectra_lexer.utils import traverse, recurse

ET = TypeVar("ET")  # Key element type.
VT = TypeVar("VT")  # Value type.


class PrefixTree(defaultdict):
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    def __init__(self):
        """ Self-referential defaultdict factory. Creates an indefinitely nested series of defaultdicts. """
        super().__init__(PrefixTree, val=[])

    def add(self, k: Sequence[ET], v: VT) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        reduce(dict.__getitem__, k, self)["val"].append(v)

    def match(self, k: Sequence[ET]) -> List[VT]:
        """ From a given sequence, return an iterable of all of the values that match
            any prefix of it in order from most elements matched to least. """
        node = self
        lst = node["val"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            lst += node["val"]
        lst.reverse()
        return lst


class Node:
    """ Class representing a node in a tree structure with linear indexing.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child list is mutable, hashing is by identity only. """

    parent = None   # Direct parent of the node. If None, it is the root node (or unconnected).
    children: list  # Direct children of the node. If empty, it is considered a leaf node.

    def __init__(self):
        self.children = []

    def add_children(self, nodes:list) -> None:
        """ Add other nodes of the same type from the given list to this node's children. """
        for n in nodes:
            n.parent = self
        self.children += nodes

    def get_ancestors(self) -> list:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return list(traverse(self, next_attr="parent"))

    def get_descendents(self) -> list:
        """ Get a list of all descendents of this node (starting with itself) down to the base. """
        return list(recurse(self, iter_attr="children"))

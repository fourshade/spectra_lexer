""" Module for recursive tree structures. """

from typing import Sequence


class PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _root: dict  # Root node of the tree. Matches the empty sequence, which is a prefix of everything.

    def __init__(self):
        self._root = {"values": []}

    def __setitem__(self, k:Sequence, v:object) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        node = self._root
        for element in k:
            node = node.get(element) or node.setdefault(element, {"values": []})
        node["values"].append(v)

    def compile(self) -> None:
        self._compile(self._root, [])

    def _compile(self, node:dict, values:list) -> None:
        """ Finalize the tree by populating nodes with values from all possible prefixes. """
        v = node.pop("values")
        v += values
        for n in node.values():
            self._compile(n, v)
        node["values"] = v

    def __getitem__(self, k:Sequence) -> list:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from shortest prefix matched to longest. """
        node = self._root
        for element in k:
            if element not in node:
                break
            node = node[element]
        return node["values"]

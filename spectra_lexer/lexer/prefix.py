from typing import Iterable, Sequence, Tuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.utils import str_without


class PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _root: dict  # Root node of the tree. Matches the empty sequence, which is a prefix of everything.

    def __init__(self):
        self._root = {"values": []}

    def add(self, k:Sequence, v:object) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        node = self._root
        for element in k:
            node = node.get(element) or node.setdefault(element, {"values": []})
        node["values"].append(v)

    def match(self, k:Sequence) -> list:
        """ From a given sequence, return an iterable of all of the values that match
            any prefix of it in order from shortest prefix matched to longest. """
        node = self._root
        lst = node["values"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            lst += node["values"]
        return lst


class OrderedKeyPrefixTree(PrefixTree):
    """ Prefix search tree that returns rules matching a prefix of ORDERED keys only. """

    _get_unordered_in: callable  # Alias for intersection with unordered keys.

    def __init__(self, unordered:Iterable[str]):
        """ Make the tree given a subset of keys that are to be treated as invisible to prefixes. """
        super().__init__()
        self._get_unordered_in = frozenset(unordered).intersection

    def add_entry(self, keys:StenoKeys, letters:str, r:object) -> None:
        """ Separate the given set of keys into ordered and unordered keys,
            Index the rule itself and the unordered keys under the ordered keys (which contain any prefix). """
        ordered, unordered = self._filter_ordered(keys)
        self.add(ordered, (r, letters, unordered))

    def prefix_match(self, keys:StenoKeys, letters:str) -> list:
        """ The rule must match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        ordered, unordered = self._filter_ordered(keys)
        return [r for (r, rl, ru) in self.match(ordered) if rl in letters and ru <= unordered]

    def _filter_ordered(self, keys:StenoKeys, _no_unordered=frozenset()) -> Tuple[str, frozenset]:
        """ Create and return an ordered string of normal keys that must be consumed starting from the left.
            Filter out the unordered keys in the first stroke that may be consumed at any time and return them too. """
        if not self._get_unordered_in(keys):
            return keys, _no_unordered
        unordered = self._get_unordered_in(keys.first_stroke())
        if not unordered:
            return keys, _no_unordered
        return str_without(keys, unordered), unordered

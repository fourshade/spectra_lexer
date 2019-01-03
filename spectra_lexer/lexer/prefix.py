from typing import Iterable, List, Tuple, TypeVar

from spectra_lexer.keys import StenoKeys
from spectra_lexer.utils import str_without_chars
from spectra_lexer.struct import PrefixTree

RT = TypeVar("RT")  # Rule type.


class OrderedKeyPrefixTree(PrefixTree):
    """ Prefix search tree that returns rules matching a prefix of ORDERED keys only. """

    _get_unordered_in: callable  # Alias for intersection with unordered keys.

    def __init__(self, unordered:Iterable[str]):
        """ Make the tree given a subset of keys that are to be treated as invisible to prefixes. """
        super().__init__()
        self._get_unordered_in = frozenset(unordered).intersection

    def add_entry(self, keys:StenoKeys, letters:str, r:RT) -> None:
        """ Separate the given set of keys into ordered and unordered keys,
            Index the rule itself and the unordered keys under the ordered keys (which contain any prefix). """
        ordered, unordered = self._filter_ordered(keys)
        self.add(ordered, (r, letters, unordered))

    def prefix_match(self, keys:StenoKeys, letters:str) -> List[RT]:
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
        ordered = str_without_chars(keys, unordered)
        return ordered, unordered

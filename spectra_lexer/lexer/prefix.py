""" Module for matching rules by a prefix of steno keys. """

from typing import Iterable, List, Sequence, TypeVar

from .base import IRuleMatcher, MATCH_TP, LexerRule


class _PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _T = TypeVar("_T")

    def __init__(self) -> None:
        """ The root node matches the empty sequence, which is a prefix of everything. """
        self._root = {"values": []}

    def add(self, k:Sequence, v:_T) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until we reach it. """
        node = self._root
        for element in k:
            if element not in node:
                node[element] = {"values": []}
            node = node[element]
        node["values"].append(v)

    def match(self, k:Sequence) -> List[_T]:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from longest prefix matched to shortest. """
        node = self._root
        values = node["values"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            values = node["values"] + values
        return values


class PrefixMatcher(IRuleMatcher):
    """ Matches rules that start with certain keys in order, and others in any order (but only within one stroke).
        The performance is heavily dependent on the number of possible unordered keys.
        Unordered matching is required for the asterisk; other keys are usually not worth the slowdown. """

    def __init__(self, key_sep:str, unordered_keys:Iterable[str]) -> None:
        filter_unordered = frozenset(unordered_keys).intersection
        self._key_sep = key_sep                    # Steno stroke delimiter.
        self._filter_unordered = filter_unordered  # Filter for unordered keys.
        self._tree = _PrefixTree()                 # Prefix tree for all rules.
        self._ordered_tree = _PrefixTree()         # Prefix tree for rules with only ordered keys.

    def add(self, rule:LexerRule) -> None:
        """ Index a rule, its skeys string, its letters, and its unordered keys under only the ordered keys.
            The ordered keys may be derived by removing the unordered keys from the full string one-at-a-time. """
        skeys = rule.skeys
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        letters = rule.letters.lower()
        # Unordered keys must be filtered from the first stroke in each string of keys.
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_set = self._filter_unordered(skeys_fs)
        if not unordered_set:
            # Add rules with only ordered keys to a separate tree for faster matching.
            self._ordered_tree.add(skeys, (rule, len(skeys), letters))
        ordered_keys = skeys
        for c in unordered_set:
            ordered_keys = ordered_keys.replace(c, "", 1)
        self._tree.add(ordered_keys, (rule, skeys, letters, unordered_set))

    def match(self, skeys:str, letters:str, *_) -> List[MATCH_TP]:
        """ Make a list of all rules that match a prefix of the ordered keys in <skeys>, a subset of <letters>,
            and a subset of <unordered_set> from the first stroke. This may yield a large number of rules.
            Also return the new key string that would result from removing the keys involved. """
        letters = letters.lower()
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_set = self._filter_unordered(skeys_fs)
        if not unordered_set:
            return self._match_ordered(skeys, letters)
        matches = []
        ordered_keys = skeys
        for c in unordered_set:
            ordered_keys = ordered_keys.replace(c, "", 1)
        for rule, r_skeys, r_letters, r_unordered in self._tree.match(ordered_keys):
            if r_letters in letters and r_unordered <= unordered_set:
                # Remove matched keys starting from the left and save the remainder.
                # With no guaranteed order, each key must be removed individually.
                skeys_left = skeys
                for c in r_skeys:
                    skeys_left = skeys_left.replace(c, "", 1)
                matches.append((rule, skeys_left, letters.find(r_letters)))
        return matches

    def _match_ordered(self, skeys:str, letters:str) -> List[MATCH_TP]:
        """ Faster match method for key strings with only ordered keys in the first stroke.
            They cannot match anything with unordered keys, and prefixes may be removed by slicing. """
        matches = []
        for rule, r_sklen, r_letters in self._ordered_tree.match(skeys):
            if r_letters in letters:
                matches.append((rule, skeys[r_sklen:], letters.find(r_letters)))
        return matches

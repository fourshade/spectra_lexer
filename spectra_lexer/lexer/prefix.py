""" Module for matching rules by a prefix of steno keys. """

from typing import Generic, Sequence, TypeVar

from . import IRuleMatcher, LexerRule, RuleMatches

E = TypeVar("E")  # Trie element type.
V = TypeVar("V")  # Trie value type.
Sequence_E = Sequence[E]
Sequence_V = Sequence[V]


class PrefixTree(Generic[E, V]):
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    def __init__(self) -> None:
        """ The root node matches the empty sequence, which is a prefix of everything. """
        self._root = {"values": []}

    def add(self, k:Sequence_E, v:V) -> None:
        """ Add a new value to the list for sequence <k>. If it doesn't exist, create nodes until we reach it. """
        node = self._root
        for element in k:
            if element not in node:
                node[element] = {"values": []}
            node = node[element]
        node["values"].append(v)

    def match(self, k:Sequence_E) -> Sequence_V:
        """ For a sequence <k>, return all of the values that match
            any prefix in order from longest prefix matched to shortest. """
        node = self._root
        values = node["values"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            values = node["values"] + values
        return values


class PrefixMatcher(IRuleMatcher):
    """ Matches rules that start with certain keys in order. """

    def __init__(self) -> None:
        self._tree = PrefixTree()  # Prefix tree for all rules.

    def add(self, rule:LexerRule) -> None:
        """ Index a rule, its skeys length, and its letters under the skeys.
            To match sentence beginnings and proper names, the letters must be converted to lowercase. """
        skeys = rule.skeys
        letters = rule.letters.lower()
        self._tree.add(skeys, (rule, len(skeys), letters))

    def match(self, skeys:str, letters:str, *_) -> RuleMatches:
        """ Match a key string with only ordered keys. Prefixes may be removed by slicing. """
        letters = letters.lower()
        matches = []
        for rule, r_sklen, r_letters in self._tree.match(skeys):
            if r_letters in letters:
                matches.append((rule, skeys[r_sklen:], letters.find(r_letters)))
        return matches


class UnorderedPrefixMatcher(IRuleMatcher):
    """ Matches rules that start with certain keys in order, and others in any order (but only within one stroke).
        The performance is heavily dependent on the number of possible unordered keys.
        Unordered matching is required for the asterisk; other keys are usually not worth the slowdown. """

    def __init__(self, key_sep:str, unordered_keys:str) -> None:
        assert len(key_sep) == 1
        self._key_sep = key_sep                    # Steno stroke delimiter.
        self._unordered_set = set(unordered_keys)  # Set of keys in which to ignore steno order.
        self._tree = PrefixTree()                  # Prefix tree for all rules.
        self._ordered_matcher = PrefixMatcher()    # Matches rules with only ordered keys.

    def add(self, rule:LexerRule) -> None:
        """ Index a rule, its skeys string, its letters, and its unordered keys under only the ordered keys.
            The ordered keys may be derived by removing the unordered keys from the full string one-at-a-time.
            To match sentence beginnings and proper names, the letters must be converted to lowercase. """
        skeys = rule.skeys
        letters = rule.letters.lower()
        # Unordered keys must be filtered from the first stroke in each string of keys.
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_fs = self._unordered_set.intersection(skeys_fs)
        if not unordered_fs:
            # Add rules with only ordered keys to a separate tree for faster matching.
            self._ordered_matcher.add(rule)
        ordered_keys = skeys
        for c in unordered_fs:
            ordered_keys = ordered_keys.replace(c, "", 1)
        self._tree.add(ordered_keys, (rule, skeys, letters, unordered_fs))

    def match(self, skeys:str, letters:str, *_) -> RuleMatches:
        """ Match all rules that contain a prefix of the ordered keys in <skeys>, a subset of <letters>,
            and a subset of unordered keys from the first stroke. This may yield a large number of rules. """
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_fs = self._unordered_set.intersection(skeys_fs)
        if not unordered_fs:
            # Use the faster tree if only ordered keys are in the first stroke.
            return self._ordered_matcher.match(skeys, letters)
        letters = letters.lower()
        matches = []
        ordered_keys = skeys
        for c in unordered_fs:
            ordered_keys = ordered_keys.replace(c, "", 1)
        for rule, r_skeys, r_letters, r_unordered in self._tree.match(ordered_keys):
            if r_letters in letters and r_unordered <= unordered_fs:
                # Remove matched keys starting from the left and save the remainder.
                # With no guaranteed order, each key must be removed individually.
                skeys_left = skeys
                for c in r_skeys:
                    skeys_left = skeys_left.replace(c, "", 1)
                matches.append((rule, skeys_left, letters.find(r_letters)))
        return matches

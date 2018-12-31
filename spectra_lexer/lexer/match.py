from __future__ import annotations
from typing import Dict, Iterable, List

from spectra_lexer.keys import first_stroke, StenoKeys
from spectra_lexer.lexer.keys import LexerKeys
from spectra_lexer.rules import StenoRule
from spectra_lexer.struct import PrefixTree

# TODO: Only attempt RARE matches after failing with the normal set of rules.
# Acceptable rule flags that indicate special behavior for the lexer's matching system.
MATCH_FLAGS = {"SPEC": "Special rule used internally (in other rules). The lexer should never know about these.",
               "WORD": "Exact word match. The parser only does a simple dict lookup for these before trying"
                       "to break a word down, so these entries do not adversely affect lexer performance.",
               "STRK": "Only matches an entire stroke, not part of one. Handled by exact stroke match.",
               "RARE": "Rule applies to very few words. The lexer should try these last, after failing with others."}


class LexerRuleMatcher:
    """ A master dictionary of steno rules. Each component maps strings to steno rules in some way. """

    _stroke_dict: Dict[StenoKeys, StenoRule]  # Rules that match by full stroke only.
    _word_dict: Dict[str, StenoRule]          # Rules that match by exact word only (whitespace-separated).
    _prefix_tree: RulePrefixTree              # Rules that match by starting with a certain number of keys in order.

    def __init__(self, rules:Iterable[StenoRule]):
        """ Construct a specially-structured series of dictionaries from an unordered iterable of finished rules. """
        # Convert rules to lexer format and sort into specific dictionaries based on their flags.
        stroke_dict = {}
        word_dict = {}
        prefix_tree = RulePrefixTree()
        for r in rules:
            flags = r.flags
            # The lexer shouldn't use internal/special rules at all. Skip them.
            if "SPEC" in flags:
                continue
            # Filter stroke and word rules into their own dicts.
            if "STRK" in flags:
                stroke_dict[r.keys] = r
            elif "WORD" in flags:
                word_dict[r.letters] = r
            # Everything else gets added to the tree-based prefix dictionary.
            # Only ordered (non-asterisk) keys determine the prefix.
            else:
                prefix_tree.add_rule(r)
        # All internal dictionaries required for active lexer operation go into instance attributes.
        self._stroke_dict = stroke_dict
        self._word_dict = word_dict
        self._prefix_tree = prefix_tree

    def match(self, keys:LexerKeys, letters:str, is_full_stroke:bool=False, is_full_word:bool=False) -> List[StenoRule]:
        """ Return a list of rules that match the given keys and letters in any of the dictionaries. """
        match_list = []
        if is_full_stroke:
            match_list += self._stroke_match(keys, letters)
        if is_full_word:
            match_list += self._word_match(keys, letters)
        match_list += self._prefix_tree.prefix_match(keys, letters)
        return match_list

    def _stroke_match(self, keys:StenoKeys, letters:str) -> List[StenoRule]:
        """ For the stroke dictionary, the rule must match the next full stroke and a subset of the given letters. """
        r = self._stroke_dict.get(first_stroke(keys))
        if r and r.letters in letters:
            return [r]
        return []

    def _word_match(self, keys:StenoKeys, letters:str) -> List[StenoRule]:
        """ For the word dictionary, the rule must match a prefix of the given keys and the next full word."""
        r = self._word_dict.get(letters.lstrip().split(" ", 1)[0])
        if r and keys.startswith(r.keys):
            return [r]
        return []


class RulePrefixTree(PrefixTree):

    def add_rule(self, r:StenoRule) -> None:
        """ Separate the given set of keys into ordered and unordered keys,
            Index the rule itself and the unordered keys under the ordered keys (which contain any prefix). """
        k = LexerKeys(r.keys)
        self.add(k.ordered, (r, k.unordered))

    def prefix_match(self, keys:LexerKeys, letters:str) -> List[StenoRule]:
        """ For the prefix dictionary, the rule must match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        return [r for (r, uk) in self.match(keys.ordered)
                if r.letters in letters and uk <= keys.unordered]

from collections import defaultdict
from functools import reduce
from typing import Dict, Iterable, List

from spectra_lexer.file import RawRulesDictionary
from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules.parser import StenoRuleParser
from spectra_lexer.rules.rules import StenoRule

# Acceptable rule flags that indicate special behavior for the lexer's matching system.
MATCH_FLAGS = {"SPEC": "Special rule used internally (in other rules). The lexer should never know about these.",
               "WORD": "Exact word match. The parser only does a simple dict lookup for these before trying"
                       "to break a word down, so these entries do not adversely affect lexer performance.",
               "STRK": "Only matches an entire stroke, not part of one. Handled by exact stroke match.",
               "RARE": "Rule applies to very few words. The lexer should try these last, after failing with others."}
MATCH_FLAG_SET = set(MATCH_FLAGS.keys())


class PrefixTree(defaultdict):
    """ A trie-based structure for figuring out steno rules applicable to a certain prefix of keys.
        It is an associative array structure with string-based keys that has the distinct advantage
        of quickly returning all values that match a given key or any of its prefixes, in order. It
        also allows duplicate keys, returning a list of all values that match it. """

    rules: List[StenoRule]  # Value of the node; contains all rules using the exact keys it took to get there.

    def __init__(self):
        """ Create a new tree node. The entire structure is a dictionary of other nodes and a list of rules. """
        super().__init__(PrefixTree)
        self.rules = []

    def add(self, k:str, v:StenoRule) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        reduce(dict.__getitem__, k, self).rules.append(v)

    def match(self, s:str) -> Iterable[StenoRule]:
        """ From a given string, return an iterable of all of the values that match
            any prefix of it in order from most characters matched to least. """
        node = self
        lst = node.rules[:]
        for char in s:
            if char not in node:
                break
            node = node[char]
            lst += node.rules
        return reversed(lst)


class LexerDictionary(object):
    """ A master dictionary of steno rules. Each component dict maps strings to steno rules in some way. """

    _stroke_dict: Dict[StenoKeys, StenoRule]  # Rules that match by full stroke only.
    _word_dict: Dict[str, StenoRule]          # Rules that match by exact word only (whitespace-separated).
    _prefix_tree: PrefixTree                  # Rules that match by starting with a certain number of keys in order.

    def __init__(self, *files:str):
        # Use the given file(s) to create a basic, unsorted rules dict.
        raw_dict = RawRulesDictionary(*files)
        # Sort the rules into specific dictionaries based on their flags.
        stroke_dict = {}
        word_dict = {}
        prefix_tree = PrefixTree()
        for v in StenoRuleParser(raw_dict):
            flags = v.flags
            # The lexer shouldn't use internal/special rules at all. Skip them.
            if "SPEC" in flags:
                continue
            # Filter stroke and word rules into their own dicts.
            if "STRK" in flags:
                stroke_dict[v.keys] = v
            elif "WORD" in flags:
                word_dict[v.letters] = v
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                prefix_tree.add(v.keys.ordered, v)
        # All internal dictionaries required for active lexer operation go into instance attributes.
        self._stroke_dict = stroke_dict
        self._word_dict = word_dict
        self._prefix_tree = prefix_tree

    def match(self, keys:StenoKeys, letters:str, is_full_stroke:bool=False, is_full_word:bool=False) -> List[StenoRule]:
        """ Return a list of all rules from each dictionary that match the given keys and letters:
            from the stroke dictionary - must match the next full stroke and a subset of the given letters.
            from the word dictionary - must match a prefix of the given keys and the next full word.
            from the prefix dictionary - must match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        match_list = []
        if is_full_stroke:
            r = self._stroke_dict.get(keys.split("/", 1)[0])
            if r and r.letters in letters:
                match_list.append(r)
        if is_full_word:
            r = self._word_dict.get(letters.lstrip().split(" ", 1)[0])
            if r and keys.startswith(r.keys):
                match_list.append(r)
        match_list.extend([r for r in self._prefix_tree.match(keys.ordered)
                           if r.letters in letters and r.keys.unordered <= keys.unordered])
        return match_list

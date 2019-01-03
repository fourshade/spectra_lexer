from typing import Dict, Generator

from spectra_lexer.keys import StenoKeys
from spectra_lexer.lexer.prefix import OrderedKeyPrefixTree
from spectra_lexer.rules import StenoRule
from spectra_lexer.utils import str_prefix

# TODO: Only attempt RARE matches after failing with the normal set of rules.
# Acceptable rule flags that indicate special behavior for the lexer's matching system.
MATCH_FLAGS = {"SPEC": "Special rule used internally (in other rules). The lexer should not match these at all.",
               "WORD": "Exact word match. The parser only does a simple dict lookup for these before trying"
                       "to break a word down, so these entries do not adversely affect lexer performance.",
               "STRK": "Only matches an entire stroke, not part of one. Handled by exact stroke match.",
               "RARE": "Rule applies to very few words. The lexer should try these last, after failing with others."}

# Steno order is not enforced for any keys in this set. This has a large performance and accuracy cost.
# Only the asterisk is used in such a way that this treatment is worth it.
KEY_STAR = "*"
_UNORDERED_KEYS = [KEY_STAR]


class LexerRuleMatcher:
    """ A master dictionary of steno rules. Each component maps strings to steno rules in some way. """

    # Separator rule constant (can be tested by identity).
    _RULE_SEP = StenoRule(StenoKeys.separator(), "", frozenset(), "Stroke separator", ())

    _special_dict: Dict[str, StenoRule]       # Rules that match by reference name.
    _stroke_dict: Dict[StenoKeys, StenoRule]  # Rules that match by full stroke only.
    _word_dict: Dict[str, StenoRule]          # Rules that match by exact word only (whitespace-separated).
    _prefix_tree: OrderedKeyPrefixTree        # Rules that match by starting with a certain number of keys in order.

    _search_callback: callable

    def __init__(self, rules_dict:Dict[str, StenoRule], search_callback):
        """ Construct a specially-structured series of dictionaries from a dict of finished rules. """
        special_dict = {}
        stroke_dict = {}
        word_dict = {}
        prefix_tree = OrderedKeyPrefixTree(_UNORDERED_KEYS)
        self._search_callback = search_callback
        # Sort rules into specific dictionaries based on their flags.
        for (n, r) in rules_dict.items():
            flags = r.flags
            # Internal rules are only used in special cases, by name.
            if "SPEC" in flags:
                special_dict[n] = r
            # Filter stroke and word rules into their own dicts.
            elif "STRK" in flags:
                stroke_dict[r.keys] = r
            elif "WORD" in flags:
                word_dict[r.letters] = r
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                prefix_tree.add_entry(r.keys, r.letters, r)
        # All internal dictionaries required for active lexer operation go into instance attributes.
        self._special_dict = special_dict
        self._stroke_dict = stroke_dict
        self._word_dict = word_dict
        self._prefix_tree = prefix_tree

    def match(self, keys, letters, all_keys, all_letters, rulemap) -> Generator:
        """ Yield rules that match the given keys and letters in any of the dictionaries. """
        # Check special single-key end-cases. There are no better matches, so return immediately if one is found.
        special_rule = self._sep_match(keys) or self._star_match(keys, all_keys, all_letters, rulemap)
        if special_rule:
            yield special_rule
            return
        # Try to match keys by prefix. This may yield a large number of rules.
        yield from self._prefix_tree.prefix_match(keys, letters)
        # We have a complete stroke next if we just started or a stroke separator was just matched.
        is_start = not rulemap
        if is_start or rulemap[-1] is self._RULE_SEP:
            stroke_rule = self._stroke_match(keys, letters)
            if stroke_rule:
                yield stroke_rule
        # We have a complete word if we just started or the word pointer is sitting on a space.
        if is_start or (letters and letters[0] == ' '):
            word_rule = self._word_match(keys, letters)
            if word_rule:
                yield word_rule

    def _star_match(self, keys:StenoKeys, all_keys:StenoKeys, all_letters:str, rulemap:list) -> StenoRule:
        """ If we only have a star left at the end of a stroke, try to match a star rule explicitly by name. """
        if keys and keys[0] == KEY_STAR and (len(keys) == 1 or keys.is_separator(1)):
            name = self._analyze_star(keys, all_keys, all_letters, rulemap)
            return self._special_dict[name]

    def _sep_match(self, keys:StenoKeys) -> StenoRule:
        """ If we end up with a stroke separator next, return its rule. """
        if keys and keys.is_separator(0):
            return self._RULE_SEP

    def _stroke_match(self, keys:StenoKeys, letters:str) -> StenoRule:
        """ For the stroke dictionary, the rule must match the next full stroke and a subset of the given letters. """
        r = self._stroke_dict.get(keys.first_stroke())
        if r and r.letters in letters:
            return r

    def _word_match(self, keys:StenoKeys, letters:str) -> StenoRule:
        """ For the word dictionary, the rule must match a prefix of the given keys and the next full word."""
        r = self._word_dict.get(str_prefix(letters.lstrip()))
        if r and keys.startswith(r.keys):
            return r

    def _analyze_star(self, keys:StenoKeys, all_keys:StenoKeys, all_letters:str, rulemap:list) -> str:
        """ Try to guess the meaning of an asterisk from the remaining keys, the full set of keys,
            the full word, and the current rulemap. Return the reference name for the best-guess rule. """
        # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
        if "." in all_letters:
            return "*:AB"
        # If the word has uppercase letters in it, it's probably a proper noun.
        if all_letters != all_letters.lower():
            return "*:PR"
        # If we have a separator key left but no recorded matches, we are at the beginning of a multi-stroke word.
        # If we have recorded separator rules but none left in the keys, we are at the end of a multi-stroke word.
        # Neither = single-stroke word, both = middle of multi-stroke word, just one = prefix/suffix.
        if keys.has_separator() ^ any(m.rule.keys.has_separator() for m in rulemap):
            return "*:PS"
        # If the search component is loaded with the standard dictionaries, we can check if there's an
        # entry with every key *except* the star. If there is, it's probably there because of a conflict.
        if self._search_callback(all_keys.without(KEY_STAR).to_rtfcre()):
            return "*:CF"
        # No other possible uses of the star are decidable by the program, so return the "ambiguous" rule.
        return "*:??"

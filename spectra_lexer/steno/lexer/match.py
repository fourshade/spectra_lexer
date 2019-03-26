from typing import Dict, List

from .prefix import OrderedKeyPrefixTree
from spectra_lexer.steno.keys import KEY_SEP, KEY_SPECIAL, StenoKeys
from spectra_lexer.steno.rules import RuleFlags, SpecialRules, StenoRule
from spectra_lexer.utils import str_prefix, str_without

# Steno order is not enforced for any keys in this set. This has a large performance and accuracy cost.
# Only the asterisk is used in such a way that this treatment is worth it.
_UNORDERED_KEYS = [StenoKeys(KEY_SPECIAL)]


class LexerRuleMatcher:
    """ A master dictionary of steno rules. Each component maps strings to steno rules in some way. """

    # Separator rule constant (can be tested by identity). This rule is uniquely owned by this class.
    _RULE_SEP = StenoRule(StenoKeys(KEY_SEP), "", frozenset(), "Stroke separator", ())

    _special_dict: Dict[str, StenoRule] = None  # Rules that match by reference name.
    _stroke_dict: Dict[str, StenoRule] = None   # Rules that match by full stroke only.
    _word_dict: Dict[str, StenoRule] = None     # Rules that match by exact word only (whitespace-separated).
    _prefix_tree: OrderedKeyPrefixTree = None   # Rules that match by starting with certain keys in order.
    _translations: Dict[str, str] = {}          # Optional translation search dict for stroke conflicts.

    def set_rules(self, rules_dict:Dict[str, StenoRule]):
        """ Construct a specially-structured series of dictionaries from a dict of finished rules. """
        special_dict = self._special_dict = {}
        stroke_dict = self._stroke_dict = {}
        word_dict = self._word_dict = {}
        prefix_tree = self._prefix_tree = OrderedKeyPrefixTree(_UNORDERED_KEYS)
        # Sort rules into specific dictionaries based on specific flags for the lexer matching system.
        match_name = RuleFlags.SPECIAL
        match_stroke = RuleFlags.STROKE
        match_word = RuleFlags.WORD
        for (n, r) in rules_dict.items():
            flags = r.flags
            # Internal rules are only used in special cases, by name.
            if match_name in flags:
                special_dict[n] = r
            # Filter stroke and word rules into their own dicts.
            elif match_stroke in flags:
                stroke_dict[r.keys] = r
            elif match_word in flags:
                word_dict[r.letters] = r
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                prefix_tree.add_entry(r.keys, r.letters, r)

    def set_translations(self, d:dict) -> None:
        """ Set up an optional translations dict for finding asterisk conflicts. """
        self._translations = d

    def match(self, keys:StenoKeys, letters:str, all_keys:StenoKeys, all_letters:str) -> List[StenoRule]:
        """ Return a list of rules that match the given keys and letters in any of the dictionaries. """
        # Check special single-key end-cases. There are no better matches, so return immediately if one is found.
        special_rule = self._sep_match(keys) or self._star_match(keys, all_keys, all_letters)
        if special_rule:
            return [special_rule]
        # Try to match keys by prefix. This may yield a large number of rules.
        matches = self._prefix_tree.prefix_match(keys, letters)
        # We have a complete stroke next if we just started or a stroke separator was just matched.
        is_start = (keys == all_keys)
        if is_start or all_keys[-len(keys)-1] == KEY_SEP:
            stroke_rule = self._stroke_match(keys, letters)
            if stroke_rule:
                matches.append(stroke_rule)
        # We have a complete word if we just started or the word pointer is sitting on a space.
        if is_start or letters[:1] == ' ':
            word_rule = self._word_match(keys, letters)
            if word_rule:
                matches.append(word_rule)
        return matches

    def _star_match(self, keys:StenoKeys, all_keys:StenoKeys, all_letters:str) -> StenoRule:
        """ If we only have a star left at the end of a stroke, try to match a star rule explicitly by name.
            The rules with these names are externally loaded, so just return None if one isn't found. """
        if keys[0] == KEY_SPECIAL == keys.strokes[0]:
            return self._analyze_star(keys, all_keys, all_letters)

    def _sep_match(self, keys:StenoKeys) -> StenoRule:
        """ If we end up with a stroke separator next, return its rule. """
        if keys[0] == KEY_SEP:
            return self._RULE_SEP

    def _stroke_match(self, keys:StenoKeys, letters:str) -> StenoRule:
        """ For the stroke dictionary, the rule must match the next full stroke and a subset of the given letters. """
        r = self._stroke_dict.get(keys.strokes[0])
        if r and r.letters in letters:
            return r

    def _word_match(self, keys:StenoKeys, letters:str) -> StenoRule:
        """ For the word dictionary, the rule must match a prefix of the given keys and the next full word."""
        r = self._word_dict.get(str_prefix(letters.lstrip()))
        if r and keys.startswith(r.keys):
            return r

    def _analyze_star(self, keys:StenoKeys, all_keys:StenoKeys, all_letters:str) -> StenoRule:
        """ Try to guess the meaning of an asterisk from the remaining keys, the full set of keys,
            the full word, and the current rulemap. Return the reference name for the best-guess rule. """
        # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
        if "." in all_letters:
            return SpecialRules.ABBREVIATION
        # If the word has uppercase letters in it, it's probably a proper noun.
        if all_letters != all_letters.lower():
            return SpecialRules.PROPER
        # If we have a multi-stroke word and are at the beginning or end of it, it's probably a prefix or suffix.
        strokes_left, all_strokes = len(keys.strokes), len(all_keys.strokes)
        if (all_strokes > 1) and (strokes_left == 1 or strokes_left == all_strokes):
            return SpecialRules.AFFIX
        # If the search component loaded a translations dict, we can check if there's an entry with every key
        # *except* the star. If there is, it's probably there because of a conflict.
        if self._translations.get(str_without(all_keys.rtfcre, KEY_SPECIAL)):
            return SpecialRules.CONFLICT
        # No other possible uses of the star are decidable by the program, so return the "ambiguous" rule.
        return SpecialRules.UNKNOWN

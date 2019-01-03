from itertools import product
from typing import Iterable, List, Optional, Tuple

from spectra_lexer import fork, on, SpectraComponent
from spectra_lexer.lexer.keys import LexerKeys
from spectra_lexer.lexer.match import LexerRuleMatcher
from spectra_lexer.lexer.rules import LexerResult
from spectra_lexer.rules import get_key_rules, StenoRule

# Separator rule constant (can be tested by identity).
_RULE_SEP = StenoRule(LexerKeys.separator(), "", frozenset(), "Stroke separator", ())


class StenoLexer(SpectraComponent):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    """

    _matcher: LexerRuleMatcher = None  # The master rule-matching dictionary.

    @on("new_rules")
    def set_rules(self, rules:Iterable[StenoRule]) -> None:
        """ Take a sequence of rules parsed from a file and sort them into categories for matching. """
        self._matcher = LexerRuleMatcher(rules)

    @fork("lexer_query", "new_lexer_result")
    def query(self, keys:str, word:str) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        pairs = [(keys, word)]
        return self._build_best_rule(pairs)

    @fork("lexer_query_product", "new_lexer_result")
    def query_best_product(self, keys:Iterable[str], words:Iterable[str]) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        pairs = list(product(keys, words))
        return self._build_best_rule(pairs)

    def _build_best_rule(self, pairs:List[Tuple[str,str]]) -> StenoRule:
        """ Given an iterable of mappings of key strings to matching translations,
            return the best possible rule relating two of them. Send it to the engine as well. """
        last_pair = pairs[0]
        built_maps = []
        for keys, word in pairs:
            # Thoroughly cleanse and parse the key string (user strokes cannot be trusted).
            last_pair = (LexerKeys.cleanse_from_rtfcre(keys), word)
            # Collect and return all valid rulemaps (that aren't optimized away) for the given pair of keys -> word.
            built_maps += self._generate_maps(*last_pair)
        # Return the default rule if no maps were found.
        if not built_maps:
            return _default_rule(*last_pair)
        # Find the highest ranked rulemap according to how accurately it (probably) mapped the stroke
        # to the translation. Make a rule out of the result and return it.
        return _best_map_to_rule(built_maps)

    def _generate_maps(self, keys:LexerKeys, word:str) -> List[LexerResult]:
        """
        Given a string of parsed steno keys and a matching translation, use steno rules to match keys to printed
        characters in order to generate a list of complete rule maps that could possibly produce the translation.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        maps = []
        best_letters = 0
        get_rule_matches = self._matcher.match
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, LexerResult(keys, word))]
        while stack:
            # Take the next search path off the stack.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            # Check special end-cases.
            if test_keys:
                s_rule = self._check_special(test_keys, rulemap)
                if s_rule is not None:
                    rulemap.add_special(s_rule, wordptr)
                    test_keys = test_keys.without(s_rule.keys)
            # If unmatched keys remain, attempt to match them to rules in steno order.
            # We assume every rule matched here MUST consume at least one key and one letter.
            if test_keys:
                # We have a complete stroke if we haven't matched anything or the last match was a stroke separator.
                is_full_stroke = (not rulemap or rulemap[-1].rule is _RULE_SEP)
                # We have a complete word if the word pointer is 0 or sitting on a space.
                is_full_word = (wordptr == 0 or (test_word and test_word[0] == ' '))
                # Calculate how many letters we could possibly skip and still be in the running for best map.
                space_left = len(test_word) - (best_letters - lc)
                # Get the rules that would work as the next match in order from last found (least keys) to first found
                # (most keys). This helps us find dense maps first so we can eliminate later ones quickly on space.
                for r in reversed(get_rule_matches(test_keys, test_word, is_full_stroke, is_full_word)):
                    # Find the first index of each match. This is also how many characters were skipped.
                    i = test_word.find(r.letters)
                    # Filter out cases that no longer have enough space left to beat or tie the best map.
                    if space_left < i:
                        continue
                    # Make a copy of the current map and add the new rule + its location in the complete word.
                    word_len = len(r.letters)
                    new_map = rulemap.copy()
                    new_map.add(r, wordptr + i, word_len)
                    # Push a stack item with the new map, and with the matched keys and letters removed.
                    word_inc = word_len + i
                    stack.append((test_keys.without(r.keys), test_word[word_inc:],
                                  wordptr + word_inc, lc + word_len, new_map))
            else:
                # If we got here, we finished a legitimate mapping that could be better than anything we've got.
                # Save the best letter count so we can reject bad maps early.
                maps.append(rulemap)
                best_letters = max(best_letters, lc)
        return maps

    def _check_special(self, test_keys:LexerKeys, rulemap) -> Optional[StenoRule]:
        """ Check special end rule cases before the main matching algorithm. """
        # If we only have a star left at the end of a stroke, consume it and try to guess its meaning.
        if test_keys.is_star(0) and (len(test_keys) == 1 or test_keys.is_separator(1)):
            flag = self._decipher_star(test_keys, rulemap)
            return get_key_rules([flag])[0]
        # If we end up with a stroke separator at the pointer, consume it and return the rule.
        if test_keys.is_separator(0):
            return _RULE_SEP

    def _decipher_star(self, test_keys:LexerKeys, rulemap:LexerResult) -> str:
        """ Try to guess the meaning of an asterisk from the remaining keys, the full set of keys,
            the full word, and the current rulemap. Return the flag value for the best-guess rule. """
        # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
        keys: LexerKeys = rulemap.keys
        letters = rulemap.letters
        if "." in letters:
            return "*:AB"
        # If the word has uppercase letters in it, it's probably a proper noun.
        if letters != letters.lower():
            return "*:PR"
        # If we have a separator key left but no recorded matches, we are at the beginning of a multi-stroke word.
        # If we have recorded separator rules but none left in the keys, we are at the end of a multi-stroke word.
        # Neither = single-stroke word, both = middle of multi-stroke word, just one = prefix/suffix.
        if test_keys.has_separator() ^ any(m.rule is _RULE_SEP for m in rulemap):
            return "*:PS"
        # If the search component is loaded with the standard dictionaries, we can check if there's an
        # entry with every key *except* the star. If there is, it's probably there because of a conflict.
        if self.engine_call("search_lookup", keys.without_star().to_rtfcre()):
            return "*:CF"
        # No other possible uses of the star are decidable by the program, so return the "ambiguous" flag.
        return "*:??"


def _best_map_to_rule(maps:Iterable[LexerResult]) -> StenoRule:
    """ Find the best out of a series of rule maps based on the rank value of each and build a rule from it. """
    best_result = max(maps, key=LexerResult.rank)
    desc = "Found {:.0%} match.".format(best_result.letters_matched_ratio())
    return StenoRule(best_result.keys, best_result.letters, frozenset(), desc, best_result.freeze())


def _default_rule(default_keys:LexerKeys, default_letters:str) -> StenoRule:
    """ Return an empty rule with default values if no rule maps were found by the lexer. """
    return StenoRule(default_keys, default_letters, frozenset(), "No matches found.", ())

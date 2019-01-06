from itertools import product
from typing import Iterable, Tuple

from spectra_lexer import fork, on
from spectra_lexer.config import Configurable
from spectra_lexer.keys import StenoKeys
from spectra_lexer.lexer.match import KEY_STAR, LexerRuleMatcher
from spectra_lexer.lexer.results import LexerResultManager
from spectra_lexer.rules import add_key_rules, RuleMapItem, StenoRule

# Separator rule constant (can be tested by identity).
_RULE_SEP = StenoRule(StenoKeys.separator(), "", frozenset(), "Stroke separator", ())


class StenoLexer(Configurable):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    """

    _matcher: LexerRuleMatcher = None    # Master rule-matching dictionary.
    _results: LexerResultManager = None  # Container and organizer of valid results for the current query.
    _keys: StenoKeys                     # Current parsed keys, used in default return rule if none others are valid.
    _word: str                           # Current English word, used in default return rule if none others are valid.

    CFG = {"need_all_keys": False}       # Do we only keep maps that have all keys covered?

    @on("start")
    def start(self, **opts) -> None:
        """ Set up the lexer results after configuration options have been set. """
        self._results = LexerResultManager(self.CFG["need_all_keys"])

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

    def _build_best_rule(self, pairs:Iterable[Tuple[str,str]]) -> StenoRule:
        """ Given an iterable of mappings of key strings to matching translations,
            return the best possible rule relating any pair of them. """
        self._results.new_query()
        # Collect all valid rulemaps (that aren't optimized away) for each pair of keys -> word.
        for keys, word in pairs:
            # Thoroughly cleanse and parse the key string first (user strokes cannot be trusted).
            self._generate_maps(StenoKeys.cleanse_from_rtfcre(keys), word)
        # Make a rule out of the best result and return it.
        return self._results.to_rule(self._keys, self._word)

    def _generate_maps(self, keys:StenoKeys, word:str) -> None:
        """
        Given a string of parsed steno keys and a matching translation, use steno rules to match keys to printed
        characters in order to generate a list of complete rule maps that could possibly produce the translation.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        self._keys = keys
        self._word = word
        best_letters = 0
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, [])]
        while stack:
            # Take the next search path off the stack.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            if not rulemap:
                # We have a complete stroke and word if we haven't matched anything yet.
                is_full_stroke = True
                is_full_word = True
            else:
                # Check special end-cases. None of these can advance the word pointer.
                # We have a complete stroke next if this match is a stroke separator.
                test_keys, is_full_stroke = self._check_special(test_keys, rulemap, wordptr)
                # We have a complete word if the word pointer is sitting on a space.
                is_full_word = (test_word and test_word[0] == ' ')
            # If unmatched keys remain, attempt to match them to rules in steno order.
            # We assume every rule matched here MUST consume at least one key and one letter.
            if test_keys:
                # Calculate how many letters we could possibly skip and still be in the running for best map.
                space_left = len(test_word) - (best_letters - lc)
                # Get the rules that would work as the next match in order from fewest keys matched to most.
                # This helps us find dense maps first so we can eliminate later ones quickly on space.
                for r in self._matcher.match(test_keys, test_word, is_full_stroke, is_full_word):
                    # Find the first index of each match. This is also how many characters were skipped.
                    i = test_word.find(r.letters)
                    # Filter out cases that no longer have enough space left to beat or tie the best map.
                    if space_left < i:
                        continue
                    # Make a copy of the current map and add the new rule + its location in the complete word.
                    word_len = len(r.letters)
                    new_map = rulemap + [RuleMapItem(r, wordptr + i, word_len)]
                    # Push a stack item with the new map, and with the matched keys and letters removed.
                    word_inc = word_len + i
                    stack.append((test_keys.without(r.keys), test_word[word_inc:],
                                  wordptr + word_inc, lc + word_len, new_map))
            else:
                # If we got here, we finished a legitimate mapping that could be better than anything we've got.
                # Save the best letter count so we can reject bad maps early.
                best_letters = max(best_letters, lc)
            # Save the map if all keys were mapped. It may not stick if partial matches are not allowed.
            self._results.add_result(rulemap, keys, word, test_keys)

    def _check_special(self, test_keys:StenoKeys, rulemap:list, wordptr:int) -> Tuple[StenoKeys, bool]:
        """ Check special end rule cases before the main matching algorithm. """
        # If we only have a star left at the end of a stroke, consume it and try to guess its meaning.
        if test_keys and test_keys[0] == KEY_STAR and (len(test_keys) == 1 or test_keys.is_separator(1)):
            flag = self._decipher_star(test_keys, rulemap)
            add_key_rules(rulemap, [flag], wordptr)
            test_keys = StenoKeys(test_keys[1:])
        # If we end up with a stroke separator at the pointer, consume it. The next stroke will be a complete one.
        if test_keys and test_keys.is_separator(0):
            rulemap.append(RuleMapItem(_RULE_SEP, wordptr, 0))
            return StenoKeys(test_keys[1:]), True
        return test_keys, False

    def _decipher_star(self, test_keys:StenoKeys, rulemap:list) -> str:
        """ Try to guess the meaning of an asterisk from the remaining keys, the full set of keys,
            the full word, and the current rulemap. Return the flag value for the best-guess rule. """
        # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
        letters = self._word
        if "." in letters:
            return "*:AB"
        # If the word has uppercase letters in it, it's probably a proper noun.
        if letters != letters.lower():
            return "*:PR"
        # If we have a separator key left but no recorded matches, we are at the beginning of a multi-stroke word.
        # If we have recorded separator rules but none left in the keys, we are at the end of a multi-stroke word.
        # Neither = single-stroke word, both = middle of multi-stroke word, just one = prefix/suffix.
        if test_keys.has_separator() ^ any(m.rule.keys.has_separator() for m in rulemap):
            return "*:PS"
        # If the search component is loaded with the standard dictionaries, we can check if there's an
        # entry with every key *except* the star. If there is, it's probably there because of a conflict.
        if self.engine_call("search_lookup", self._keys.without(KEY_STAR).to_rtfcre()):
            return "*:CF"
        # No other possible uses of the star are decidable by the program, so return the "ambiguous" flag.
        return "*:??"

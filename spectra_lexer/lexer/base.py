from functools import partial
from itertools import product
from typing import Dict, Iterable, Tuple

from spectra_lexer import Component, fork, on
from spectra_lexer.config import CFGOption
from spectra_lexer.keys import StenoKeys
from spectra_lexer.lexer.match import LexerRuleMatcher
from spectra_lexer.lexer.results import LexerResults
from spectra_lexer.rules import RuleMapItem, StenoRule


class StenoLexer(Component):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    """

    ROLE = "lexer"
    need_all_keys: bool = CFGOption(False, "Need All Keys", "Only return results that match every key in the stroke.")

    _matcher: LexerRuleMatcher = None  # Master rule-matching dictionary.
    _results: LexerResults = None      # Container and organizer of valid results for the current query.

    @on("new_rules")
    def set_rules(self, rules_dict:Dict[str, StenoRule]) -> None:
        """ Set up the rule matcher with a dict of rules and a translation search callback. """
        search_callback = partial(self.engine_call, "search_lookup")
        self._matcher = LexerRuleMatcher(rules_dict, search_callback)

    @fork("lexer_query", "new_lexer_result")
    def query(self, keys:str, word:str) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        pair = (keys, word)
        return self._build_best_rule([pair], pair)

    @fork("lexer_query_product", "new_lexer_result")
    def query_product(self, keys:Iterable[str], words:Iterable[str]) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        pairs = list(product(keys, words))
        return self._build_best_rule(pairs, pairs[0])

    def _build_best_rule(self, pairs:Iterable[Tuple[str,str]], default_pair:Tuple[str,str]) -> StenoRule:
        """ Given an iterable of mappings of key strings to matching translations,
            return the best possible rule relating any pair of them. """
        self._results = LexerResults(self.need_all_keys)
        # Collect all valid rulemaps (that aren't optimized away) for each pair of keys -> word.
        for keys, word in pairs:
            # Thoroughly cleanse and parse the key string first (user strokes cannot be trusted).
            self._generate_maps(StenoKeys.cleanse_from_rtfcre(keys), word)
        # Make a rule out of the best result (if any) and return it.
        return self._results.to_rule(default_pair)

    def _generate_maps(self, keys:StenoKeys, word:str) -> None:
        """
        Given a string of parsed steno keys and a matching translation, use steno rules to match keys to printed
        characters in order to generate a list of complete rule maps that could possibly produce the translation.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        best_letters = 0
        add_result = self._results.add_result
        match_rules = self._matcher.match
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, [])]
        while stack:
            # Take the next search path off the stack and add it to the results if it's not empty.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            if rulemap:
                add_result(rulemap, keys, word, test_keys)
            if not test_keys:
                # If no keys are left, we finished a complete mapping that could be better than anything we've got.
                # Save the best letter count (so we can reject bad maps early) and continue up the stack.
                best_letters = max(best_letters, lc)
                continue
            # If unmatched keys remain, attempt to match them to rules in steno order.
            # Calculate how many letters we could possibly skip and still be in the running for best map.
            space_left = len(test_word) - (best_letters - lc)
            # Get the rules that would work as the next match in order from fewest keys matched to most.
            # This helps us find dense maps first so we can eliminate later ones quickly on space.
            for r in match_rules(test_keys, test_word, keys, word, rulemap):
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

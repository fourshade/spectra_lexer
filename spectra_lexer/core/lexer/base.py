from itertools import product
from typing import Dict, Generator, Iterable, List

from spectra_lexer import Component, fork, on
from spectra_lexer.config import CFGOption
from spectra_lexer.core.lexer.match import LexerRuleMatcher
from spectra_lexer.core.lexer.results import LexerResult
from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMapItem, StenoRule


class StenoLexer(Component):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    """

    ROLE = "lexer"
    need_all_keys: bool = CFGOption(False, "Need All Keys", "Only return results that match every key in the stroke.")

    _matcher: LexerRuleMatcher  # Master rule-matching dictionary.

    def __init__(self) -> None:
        """ Set up the matcher with an empty rule dictionary. """
        super().__init__()
        self._matcher = LexerRuleMatcher()

    @on("new_rules")
    def set_rules(self, rules_dict:Dict[str, StenoRule]) -> None:
        """ Set up the rule matcher with a dict of rules. """
        self._matcher.set_rules(rules_dict)

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Set up the rule matcher with an optional translations dict for asterisks. """
        self._matcher.set_translations(d)

    @fork("lexer_query", "new_lexer_result")
    def query(self, keys:str, word:str) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        return LexerResult.best_rule(self._gather_results(keys, word), default=(keys, word))

    @fork("lexer_query_product", "new_lexer_result")
    def query_product(self, keys:Iterable[str], words:Iterable[str]) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        pairs = list(product(keys, words))
        results = [result for keys, word in pairs for result in self._gather_results(keys, word)]
        return LexerResult.best_rule(results, default=pairs[0])

    @fork("lexer_query_map", "new_lexer_result_list")
    def query_map(self, keys:Iterable[str], words:Iterable[str], mapfn=map) -> List[StenoRule]:
        """ Take iterables of keys and words and return the best rule for each pair in a list.
            This can be done with map(), or with ProcessPoolExecutor.map() to use multiple processes in parallel. """
        return list(mapfn(self.query, keys, words))

    def _gather_results(self, keys:str, word:str) -> List[LexerResult]:
        """ Generate a list of results for a translation with all required parameters for ranking. """
        # Thoroughly cleanse and parse the key string first (user strokes cannot be trusted).
        keys = StenoKeys.cleanse_from_rtfcre(keys)
        # Collect all valid rulemaps (that aren't optimized away) for the translation keys -> word.
        r_iter = self._generate_maps(keys, word)
        return [LexerResult(rulemap, test_keys, keys, word) for rulemap, test_keys in r_iter]

    def _generate_maps(self, keys:StenoKeys, word:str) -> Generator:
        """
        Given a string of parsed steno keys and a matching translation, use steno rules to match keys to printed
        characters in order to generate a series of complete rule maps that could possibly produce the translation.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        best_letters = 0
        match_rules = self._matcher.match
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, [])]
        while stack:
            # Take the next search path off the stack and yield the rulemap if it's not empty.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            if rulemap:
                # If we need all keys to be matched, don't yield incomplete maps.
                if not test_keys or not self.need_all_keys:
                    yield rulemap, test_keys
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

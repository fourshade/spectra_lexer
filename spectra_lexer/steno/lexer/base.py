from itertools import product
from typing import Dict, Generator, Iterable, List, Callable

from .match import LexerRuleMatcher
from .results import LexerResult, LexerResultRanker
from spectra_lexer import Component
from spectra_lexer.steno.rules import RuleMapItem, StenoRule
from spectra_lexer.steno.system import StenoSystem
from spectra_lexer.utils import str_without


class StenoLexer(Component):
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    need_all_keys = Resource("config", "lexer:need_all_keys", False,
                             "Only return results that match every key in the stroke.")

    _matcher: LexerRuleMatcher          # Master rule-matching dictionary.
    _ranker: LexerResultRanker          # Ranks lexer results according to approximate "correctness".
    _cleanse: Callable[[str], str]      # Performs thorough conversions on RTFCRE steno strings.
    _translations: Dict[str, str] = {}  # Optional translation search dict for mass queries.

    def __init__(self):
        """ Set up the matcher with an empty rule dictionary. """
        super().__init__()
        self._matcher = LexerRuleMatcher()
        self._ranker = LexerResultRanker()

    @on("set_system")
    def set_system(self, system:StenoSystem) -> None:
        self._cleanse = system.cleanse_from_rtfcre
        self._matcher.load(system)
        self._ranker.set_converter(system.to_rtfcre)

    @on("set_dict_translations")
    def set_translations(self, d:dict) -> None:
        self._matcher.set_translations(d)
        self._translations = d

    @on("lexer_query", pipe_to="new_output")
    def query(self, keys:str, word:str) -> StenoRule:
        """ Return and send out the best rule that maps the given key string to the given word. """
        return self._ranker.best_rule(self._gather_results(keys, word), default=(keys, word))

    @on("lexer_query_product", pipe_to="new_output")
    def query_product(self, keys:Iterable[str], words:Iterable[str]) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return and send out the best rule out of all combinations. """
        pairs = list(product(keys, words))
        results = [result for keys, word in pairs for result in self._gather_results(keys, word)]
        return self._ranker.best_rule(results, default=pairs[0])

    @on("lexer_query_all", pipe_to="new analysis")
    def query_all(self, items:Iterable[tuple]=None, filter_in=None, filter_out=None, save=True) -> List[StenoRule]:
        """ Run the lexer in parallel on all (keys, word) translations in <items> and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward.
            If no items are provided, the last loaded set of translations is used. Results are saved afterwards. """
        if items is None:
            items = self._translations.items()
        # Only keep results with all keys matched to reduce garbage.
        # Delete the attribute when finished to re-expose the class config setting.
        self.need_all_keys = True
        results = self.engine_call("parallel_starmap", self.query, filter(filter_in, items))
        results = list(filter(filter_out, results))
        del self.need_all_keys
        if save:
            self.engine_call("rules_save", results)
        return results

    def _gather_results(self, keys:str, word:str) -> List[LexerResult]:
        """ Generate a list of results for a translation with all required parameters for ranking. """
        # Thoroughly cleanse and parse the key string into s-keys format first (user strokes cannot be trusted).
        skeys = self._cleanse(keys)
        # Collect all valid rulemaps (that aren't optimized away) for the translation keys -> word.
        r_iter = self._generate_maps(skeys, word)
        return [LexerResult(rulemap, test_skeys, skeys, word) for rulemap, test_skeys in r_iter]

    def _generate_maps(self, skeys:str, word:str) -> Generator:
        """
        Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
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
        stack = [(skeys, word.lower(), 0, 0, [])]
        while stack:
            # Take the next search path off the stack and yield the rulemap if it's not empty.
            test_skeys, test_word, wordptr, lc, rulemap = stack.pop()
            if rulemap:
                # If we need all keys to be matched, don't yield incomplete maps.
                if not test_skeys or not self.need_all_keys:
                    yield rulemap, test_skeys
            if not test_skeys:
                # If no keys are left, we finished a complete mapping that could be better than anything we've got.
                # Save the best letter count (so we can reject bad maps early) and continue up the stack.
                best_letters = max(best_letters, lc)
                continue
            # If unmatched keys remain, attempt to match them to rules in steno order.
            # Calculate how many letters we could possibly skip and still be in the running for best map.
            space_left = len(test_word) - (best_letters - lc)
            # Get the rules that would work as the next match in order from fewest keys matched to most.
            # This helps us find dense maps first so we can eliminate later ones quickly on space.
            for (r, rskeys, rletters) in match_rules(test_skeys, test_word, skeys, word):
                # Find the first index of each match. This is also how many characters were skipped.
                i = test_word.find(rletters)
                # Filter out cases that no longer have enough space left to beat or tie the best map.
                if space_left < i:
                    continue
                # Make a copy of the current map and add the new rule + its location in the complete word.
                word_len = len(rletters)
                new_map = rulemap + [RuleMapItem(r, wordptr + i, word_len)]
                # Push a stack item with the new map, and with the matched keys and letters removed.
                word_inc = word_len + i
                stack.append((str_without(test_skeys, rskeys), test_word[word_inc:],
                              wordptr + word_inc, lc + word_len, new_map))

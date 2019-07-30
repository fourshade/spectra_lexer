from typing import Callable, Iterable, Iterator, List, Tuple

from .generate import LexerRuleGenerator, RESULT_TYPE
from .match import LexerRuleMatcher
from .parallel import ParallelMapper
from spectra_lexer.resource import KeyLayout, RulesDictionary, RuleMapItem, StenoRule


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    _match_rules: LexerRuleMatcher      # Master rule-matching dictionary.
    _generate_rule: LexerRuleGenerator  # Makes rules from lexer matches.
    _to_skeys: Callable[[str], str]     # Performs thorough conversions on RTFCRE steno strings.

    def __init__(self, layout:KeyLayout, rules:RulesDictionary):
        self._match_rules = LexerRuleMatcher(layout, rules)
        self._generate_rule = LexerRuleGenerator(layout.to_rtfcre)
        self._to_skeys = layout.cleanse_from_rtfcre

    def query(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return the best rule that maps the given key string to the given word. """
        results = [*self._process(keys, word, **kwargs)]
        return self._generate_rule(results, keys, word)

    def query_best(self, items:Iterable[Tuple[str, str]], **kwargs) -> StenoRule:
        """ Return the best rule out of all (keys, word) pairs. """
        first, *others = pairs = [*items]
        results = [r for keys, word in pairs for r in self._process(keys, word, **kwargs)]
        return self._generate_rule(results, *first)

    def query_parallel(self, items:Iterable[Tuple[str, str]],
                       filter_in:Callable=None, filter_out:Callable=None, **kwargs) -> List[StenoRule]:
        """ Run the lexer in parallel on all translation items and return a list of results.
            <filter_in> eliminates translations before processing, and <filter_out> eliminates results afterward. """
        mapper = ParallelMapper(self.query, **kwargs)
        if filter_in is not None:
            items = filter(filter_in, items)
        results = mapper.starmap(items)
        if filter_out is not None:
            results = list(filter(filter_out, results))
        return results

    def _process(self, keys:str, word:str, match_all_keys:bool=False) -> Iterator[RESULT_TYPE]:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of complete rule maps that could possibly produce the translation.
            Yield each result that isn't optimized away. Use heavy optimization when possible.
            If <match_all_keys> is True, only return results that match every key in the stroke."""
        match_rules = self._match_rules
        # Thoroughly cleanse and parse the key string into s-keys format first (user strokes cannot be trusted).
        all_skeys = self._to_skeys(keys)
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        lword = word.lower()
        # The queue is a list of tuples, each containing the state of the lexer at some point in time.
        # Each tuple includes the keys not yet matched, the current position in the word, and the current rule map.
        # Initialize the queue with the start position ready and start processing.
        queue = [(all_skeys, 0, [])]
        queue_add = queue.append
        # Simple iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator pointer can be considered the start of the queue.
        for skeys, wordptr, rulemap in queue:
            letters_left = lword[wordptr:]
            # Get the rules that would work as the next match in order from fewest keys matched to most.
            for r, r_skeys, r_letters, r_skeys_len, r_letters_len in match_rules(skeys, letters_left, all_skeys, word):
                # Make a copy of the current map and add the new rule + its location in the word.
                new_wordptr = wordptr + letters_left.find(r_letters)
                new_map = rulemap + [RuleMapItem(r, new_wordptr, r_letters_len)]
                # Remove all matched keys and keep the remainder.
                if skeys[:r_skeys_len] == r_skeys:
                    # Fast path: if the keys are a direct prefix, just cut it off.
                    skeys_left = skeys[r_skeys_len:]
                else:
                    # Otherwise, each key must be removed individually.
                    skeys_left = skeys
                    for c in r_skeys:
                        skeys_left = skeys_left.replace(c, "", 1)
                # A "complete" map is one that matches every one of the keys to a rule.
                # If we need all keys to be matched, don't add incomplete maps.
                if not skeys_left or not match_all_keys:
                    yield new_map, skeys_left, keys, word
                    if not skeys_left:
                        # If all keys are matched, continue without adding to the queue.
                        continue
                # Add a queue item with the remaining keys, the new position in the word, and the new map.
                queue_add((skeys_left, new_wordptr + r_letters_len, new_map))

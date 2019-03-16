""" Module for the batch components of Spectra. These handle bulk data operations in parallel. """

from collections import defaultdict
from functools import partial
from time import time
from traceback import print_exc
from typing import Dict, Iterable

from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule


class BatchProcessor(Component):
    """ Base class component for batch mode operations. """

    @on("run")
    def run(self) -> int:
        """ Run the required operations and print the execution time. """
        s_time = time()
        print(f"Operation started.")
        self.operation()
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

    def operation(self) -> None:
        """ Add the main operation to a subclass here. """
        raise NotImplementedError

    def map(self, key:str, *iterables:Iterable) -> list:
        """ Map an engine command in parallel over all items in one or more iterables. Order is not guaranteed.
            If the parallel component fails or is not loaded, do it using a regular map function instead.
            Parallel ops are typically all-or-nothing, so consumable iterators should be safe to retry on failure. """
        try:
            results = self.engine_call("parallel_map", key, *iterables)
        except Exception:
            results = None
            print_exc()
        if results is None:
            print("Parallel operation failed. Trying with a single process...")
            results = list(map(partial(self.engine_call, key), *iterables))
        return results

    def starmap(self, key:str, iterable:Iterable) -> list:
        """ Equivalent of itertools.starmap() for an engine command. """
        return self.map(key, *zip(*iterable))


class BatchAnalyzer(BatchProcessor):
    """ Batch operations class for working with the lexer and steno translations. """

    _translations: Dict[str, str] = {}  # Main translations dict to process.
    filter_in = None                    # Filter function to eliminate translations before reaching the lexer.

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Set the translations dict to be processed with query_all(). """
        self._translations = d

    def operation(self) -> None:
        """ Run the lexer in parallel on all translations and save the results. """
        results = self.query_all()
        self.engine_call("rules_save", results)

    def filter_out(self, rule) -> bool:
        """ Filter function to eliminate lexer results before they are saved. """
        # Results with zero or one children are either unmatched or are a basic rule themselves.
        return len(rule.rulemap) > 1

    def query_all(self) -> list:
        """ Run the lexer in parallel on all translations. We only keep lexer results that matched all the keys. """
        self.engine_call(f"set_config_lexer:need_all_keys", True)
        results = self.starmap("lexer_query", filter(self.filter_in, self._translations.items()))
        return list(filter(self.filter_out, results))


class BatchIndexer(BatchAnalyzer):
    """ Batch operations class for making a steno translation analysis into a full rules index. """

    size = Option("cmdline", "index-size", 12, "Determines the relative size of a generated index:\n"
                                               "index-size <= 0:  includes nothing.\n"
                                               "index-size == 10: fast index with relatively simple words.\n"
                                               "index-size == 12: average-sized index (default).\n"
                                               "index-size == 15: slower index with more advanced words.\n"
                                               "index-size >= 20: includes everything.")

    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.

    @on("new_rules_reversed")
    def set_rules_reversed(self, rd:Dict[StenoRule, str]) -> None:
        """ Set up the reverse rule dict. """
        self._rev_rules = rd

    def operation(self) -> None:
        """ Generate a set of rules from the lexer using translations and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every lexer translation that used it. """
        if self.size >= 20:
            self.filter_in = None
        results = self.query_all()
        translation_lists = self._count_rules(results)
        index = self._sort_translations(translation_lists)
        self.engine_call("index_save", index)

    def filter_in(self, translation) -> bool:
        """ Filter function to eliminate larger entries from the index depending on the size factor. """
        keys, word = translation
        return len(keys) <= self.size and len(word) <= self.size

    def _count_rules(self, results) -> Dict[str, list]:
        """ From the lexer rulemaps, make lists of all translations that use each built-in rule at the top level. """
        rulecounter = defaultdict(list)
        for rs in results:
            for item in rs.rulemap:
                rule = item.rule
                rulecounter[rule].append((rs.keys.rtfcre, rs.letters))
        return rulecounter

    def _sort_translations(self, translation_lists:Dict[str, list]) -> Dict[str, dict]:
        """ From the dict of lists, sort all translations in each list and convert the rule keys to strings.
            After sorting, turn each list into a dict. The dicts will preserve this ordering when saved to disk. """
        keys = map(self._rev_rules.get, translation_lists.keys())
        values = map(dict, map(sorted, translation_lists.values()))
        index = dict(zip(keys, values))
        # Hardcoded rules and missing rules end up under the key None after conversion.
        # These entries are useless, and None is not a valid key in JSON, so toss it.
        if None in index:
            del index[None]
        return index

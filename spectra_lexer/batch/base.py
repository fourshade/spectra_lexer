from collections import defaultdict
from functools import partial
from time import time
from traceback import print_exc
from typing import Dict

from spectra_lexer import Component


class BatchProcessor(Component):
    """ Base class component for batch mode operations. """

    @on("run")
    def run(self) -> int:
        """ Run the required operations and print the execution time. """
        s_time = time()
        print(f"Analysis started.")
        self.operation()
        print(f"Analysis done in {time() - s_time:.1f} seconds.")
        return 0

    def operation(self) -> None:
        """ Add the main operation to a subclass here. """
        raise NotImplementedError

    def parallel_map(self, key:str, *iterables):
        """ Map an engine command in parallel on all items in one or more iterables.
            If the parallel component is not working, do it using the regular map() function. """
        try:
            results = self.engine_call("parallel_map", key, *iterables)
        except Exception:
            results = None
            print_exc()
        if results is None:
            print("Parallel operation failed. Trying with a single process...")
            results = list(map(partial(self.engine_call, key), *iterables))
        return results


class BatchAnalyzer(BatchProcessor):
    """ Batch operations class for working with steno translations. """

    _translations: Dict[str, str] = {}  # Main translations dict to process.

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Set the translations dict to be processed with query_all(). """
        self._translations = d

    def operation(self) -> None:
        """ Run the lexer in parallel on all translations and save the results. """
        results = self.query_all()
        self.engine_call("rules_save", results)

    def query_all(self) -> list:
        """ Run the lexer in parallel on all translations. """
        d = self._translations
        results = self.parallel_map("lexer_query", d.keys(), d.values())
        return results


class BatchIndexer(BatchAnalyzer):
    """ Batch operations class for making a steno translation analysis into a full rules index. """

    def operation(self) -> None:
        """ Generate a set of rules from the lexer using translations and compare them to the built-in rules.
            Make a index for each built-in rule containing a dict of every lexer translation that used it.
            We only use lexer results that matched all the keys. This is still a very heavy operation. """
        results = self.query_all()
        translation_lists = self.count_rules(results)
        index = self.sort_translations(translation_lists)
        # Results with hardcoded rules will end up under None. This includes almost everything, so toss that entry.
        if None in index:
            del index[None]
        self.engine_call("index_save", index)

    def count_rules(self, results) -> Dict[str, list]:
        """ From the lexer rulemaps, make lists of all translations that use each built-in rule at the top level. """
        rulecounter = defaultdict(list)
        for rs in results:
            for item in rs.rulemap:
                rule = item.rule
                rulecounter[rule].append((rs.keys.rtfcre, rs.letters))
        return rulecounter

    def sort_translations(self, translation_lists:Dict[str, list]) -> Dict[str, dict]:
        """ From the dict of lists, sort all translations in each list and add them in order to a dict. """
        values = map(dict, map(sorted, translation_lists.values()))
        index = dict(zip(translation_lists.keys(), values))
        return index

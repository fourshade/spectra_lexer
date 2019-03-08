from time import time
from typing import Dict

from spectra_lexer import Component


class BatchProcessor(Component):
    """ Master component for batch mode operations. """

    _translations: Dict[str, str] = {}  # Main translations dict to process.

    @respond_to("run")
    def run(self) -> int:
        """ Run the lexer in parallel on all translations, save the results, and print the execution time. """
        s_time = time()
        print(f"Analysis started.")
        iterables = (self._translations.keys(), self._translations.values())
        results = self.engine_call("parallel_map", "lexer_query", *iterables)
        self.engine_call("rules_save", results)
        print(f"Analysis done in {time() - s_time:.1f} seconds.")
        return 0

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Set the translations dict to be processed on run(). """
        self._translations = d

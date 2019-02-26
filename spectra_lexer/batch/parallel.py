from concurrent.futures import ProcessPoolExecutor
from functools import partial
from os import cpu_count

from spectra_lexer import Component, on, pipe


class ParallelExecutor(Component):
    """ Component to run the lexer in parallel on a translation dictionary. """

    ROLE = "parallel"

    _translations: dict = {}  # Translations dict to parse.

    @pipe("start", "rules_save")
    def run(self, processes=None) -> list:
        """ Run each translation through the lexer and save the results to a rules file. """
        # Use ProcessPoolExecutor.map() to run the lexer in multiple processes in parallel.
        # The lexical analysis does not mutate any global state, so it is thread/process-safe.
        d = self._translations
        # The number of processes defaults to the number of CPU cores.
        workers = processes or cpu_count() or 1
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # For best performance, split the work up into a single large chunk for each process.
            mapfn = partial(executor.map, chunksize=(len(d) // workers))
            results = self.engine_call("lexer_query_map", d.keys(), d.values(), mapfn=mapfn)
        return results

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Save the translation dictionary for later parsing. This must happen before this component starts. """
        self._translations = d

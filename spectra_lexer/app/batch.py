from concurrent.futures import ProcessPoolExecutor
from functools import partial
from os import cpu_count
from time import time

from spectra_lexer import Component, pipe, on
from spectra_lexer.app import SpectraApplication


class BatchExecutor(Component):
    """ Class for operation of the Spectra program in batch mode on a translation dictionary. """

    @pipe("start", "rules_save")
    def start(self, *, out:str, processes:int, **opts) -> tuple:
        """ Run each translation through the lexer and save the results to a rules file. """
        # Use ProcessPoolExecutor.map() to run the lexer in multiple processes in parallel.
        # The lexical analysis does not mutate any global state, so it is thread/process-safe.
        d = self.d
        workers = processes or cpu_count() or 1
        # By default this is the number of CPU cores.
        with ProcessPoolExecutor(max_workers=workers) as executor:
            mapfn = partial(executor.map, chunksize=(len(d) // workers))
            results = self.engine_call("lexer_query_map", d.keys(), d.values(), mapfn=mapfn)
        return out, results

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        self.d = d


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself in batch mode. """
    # The script will exit after processing all <translations> and saving the rules to <out>.
    s_time = time()
    app = SpectraApplication(BatchExecutor)
    app.start(translations=(), out="output.json", processes=None)
    print("Processing done in {:.1f} seconds.".format(time() - s_time))


if __name__ == '__main__':
    main()

""" Main module for batch console applications. """

import sys
from time import time

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.resource.translations import TranslationFilter as Fcls


def main() -> int:
    """ Analyze translations files and create an examples index from them. Time the execution. """
    opts = SpectraOptions("Batch script for creating an examples index.")
    opts.add("size", Fcls.SIZE_DEFAULT, f"Relative size of generated index ({Fcls.SIZE_MINIMUM}-{Fcls.SIZE_MAXIMUM}).")
    opts.add("processes", 0, "Number of processes used for parallel execution (0 = one per CPU core).")
    spectra = Spectra(opts)
    log = spectra.logger.log
    log("Compiling examples index...")
    start_time = time()
    io = spectra.resource_io
    analyzer = spectra.analyzer
    files_in = spectra.translations_paths
    file_out = spectra.index_path
    translations = io.load_json_translations(*files_in)
    pairs = Fcls(opts.size).filter(translations.items())
    examples = analyzer.compile_index(pairs, process_count=opts.processes)
    io.save_json_examples(file_out, examples)
    total_time = time() - start_time
    log(f"Index complete in {total_time:.1f} seconds.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

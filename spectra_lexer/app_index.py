""" Main module for batch console applications. """

import sys
from time import time

from spectra_lexer import SpectraOptions
from spectra_lexer.analysis import TranslationFilter


def main() -> int:
    """ Analyze translations files and create an examples index from them. Time the execution. """
    opts = SpectraOptions("Batch script for creating an examples index.")
    fcls = TranslationFilter
    opts.add("size", fcls.SIZE_MEDIUM, f"Relative size of generated index ({fcls.SIZE_MINIMUM}-{fcls.SIZE_MAXIMUM}).")
    opts.add("processes", 0, "Number of processes used for parallel execution (0 = one per CPU core).")
    spectra = opts.compile()
    files_in = opts.translations_paths()
    file_out = opts.index_path()
    log = spectra.log
    io = spectra.translations_io
    analyzer = spectra.analyzer
    log("Operation started...")
    start_time = time()
    translations = io.load_json_translations(*files_in)
    pairs = translations.items()
    index = analyzer.compile_index(pairs, size=opts.size, process_count=opts.processes)
    examples = {r_id: dict(pairs_out) for r_id, pairs_out in index.items()}
    io.save_json_examples(file_out, examples)
    total_time = time() - start_time
    log(f"Operation done in {total_time:.1f} seconds.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

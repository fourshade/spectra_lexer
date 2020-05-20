""" Main module for batch console applications. """

import sys
from time import time

from spectra_lexer import Spectra
from spectra_lexer.analysis import TranslationFilter
from spectra_lexer.util.cmdline import CmdlineOptions


def main() -> int:
    """ Analyze translations files and create an examples index from them. Time the execution. """
    opts = CmdlineOptions("Batch script for creating an examples index.")
    opts.add("size", TranslationFilter.SIZE_MEDIUM, "Relative size of generated index.")
    opts.add("processes", 0, "Number of processes used for parallel execution (0 = one per CPU core).")
    spectra = Spectra(opts)
    spectra.log("Operation started...")
    start_time = time()
    engine = spectra.build_engine()
    files_in = spectra.translations_paths()
    engine.load_translations(*files_in)
    file_out = spectra.index_path()
    engine.compile_examples(opts.size, file_out, process_count=opts.processes)
    total_time = time() - start_time
    spectra.log(f"Operation done in {total_time:.1f} seconds.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

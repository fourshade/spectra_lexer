import sys
from time import time

from spectra_lexer.base import StenoAppFactory, StenoAppOptions
from spectra_lexer.cmdline import CmdlineOption


class IndexAppOptions(StenoAppOptions):
    """ Contains all command-line options necessary to build a app and make an index. """

    # None does not work as a default value, so represent it with the sentinel value -1.
    index_size: int = CmdlineOption("--size", -1, "Relative size of generated index.")
    processes: int = CmdlineOption("--processes", 0, "Number of processes used for parallel execution.")


def main() -> int:
    """ Analyze translations files and create an index from them. Time the execution. """
    options = IndexAppOptions(__doc__)
    options.parse()
    factory = StenoAppFactory(options)
    log = factory.build_logger().log
    log("Loading...")
    app = factory.build_app()
    log("Loading complete.")
    index_size = None if options.index_size < 0 else options.index_size
    process_count = options.processes
    start_time = time()
    log("Operation started...")
    app.make_index(index_size, processes=process_count)
    total_time = time() - start_time
    log(f"Operation done in {total_time:.1f} seconds.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

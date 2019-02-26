from time import time

from spectra_lexer.batch.parallel import ParallelExecutor
from spectra_lexer.core import CoreApplication


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself in batch mode. """
    # The script will exit after processing all translations and saving the rules.
    s_time = time()
    app = CoreApplication(ParallelExecutor)
    app.start()
    print(f"Processing done in {time() - s_time:.1f} seconds.")


if __name__ == '__main__':
    main()

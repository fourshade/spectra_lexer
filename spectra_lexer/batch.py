from time import time

from spectra_lexer import core
from spectra_lexer.app import Application


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself in batch mode.
        The script will exit after processing all translations and saving the rules. """
    s_time = time()
    app = Application(*core.COMPONENTS)
    app.start()
    # Run the lexer in parallel on all translations, save the results, and print the execution time.
    results = app.call("lexer_query_map")
    app.call("rules_save", results)
    print(f"Processing done in {time() - s_time:.1f} seconds.")


if __name__ == '__main__':
    main()

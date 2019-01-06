from functools import partial
from itertools import starmap
import sys

from spectra_lexer.app import SpectraApplication


class BatchApplication(SpectraApplication):
    """ Class for operation of the Spectra program in batch mode on a translation dictionary. """

    def start(self, file_in:str, file_out:str, *cmd_args:str, **opts) -> None:
        """ Load translations from a file, run each one through the lexer, and save the results to a rules file. """
        super().start(*cmd_args, **opts)
        d = self.engine.call("dict_load_translations", file_in)
        call_lexer = partial(self.engine.call, "lexer_query")
        results = list(starmap(call_lexer, d.items()))
        self.engine.call("dict_save_rules", file_out, results)


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself in batch mode. """
    # The script will exit after processing all translations in the first file and saving the rules to the second.
    app = BatchApplication()
    try:
        app.start(*sys.argv[1:])
        print("Processing done.")
    except TypeError:
        print("Not enough arguments. Need a translation input file and a rule output file.")


if __name__ == '__main__':
    main()

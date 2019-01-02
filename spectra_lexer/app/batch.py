from functools import partial
from itertools import starmap
import sys

from spectra_lexer.app import SpectraApplication


class BatchApplication(SpectraApplication):
    """ Class for operation of the Spectra program in batch mode on a translation dictionary. """

    def start(self, file_in, file_out, **cfg_dict) -> None:
        """ Load translations from a file, run each one through the lexer, and save the results to a rules file. """
        super().start(**cfg_dict)
        d = self.engine.call("file_load", file_in)
        call_lexer = partial(self.engine.call, "lexer_query")
        results = list(starmap(call_lexer, d.items()))
        self.engine.call("dict_save_rules", file_out, results)


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself in batch mode. """
    if len(sys.argv) < 3:
        print("Not enough arguments. Need a translation input file and a rule output file.")
        return
    # The script will exit after processing all translations in file_in and saving the result rules to file_out.
    app = BatchApplication()
    app.start(file_in=sys.argv[1], file_out=sys.argv[2])
    print("Processing done.")


if __name__ == '__main__':
    main()

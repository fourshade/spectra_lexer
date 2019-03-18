""" Module for the batch components of Spectra. These handle bulk data operations in parallel. """

from time import time

from spectra_lexer import Component


class BatchProcessor(Component):
    """ Batch operations class for working with the lexer, steno translations, and indices. """

    operation = Option("cmdline", "operation", "analyze", "Operation sequence to run in batch mode.")

    _translations: dict = {}  # Main translations dict to process.

    @on("new_translations")
    def set_translations(self, d:dict) -> None:
        """ Set the translations dict to be processed with lexer_query_all. """
        self._translations = d

    @on("run")
    def run(self) -> int:
        """ Run the required operation and print the execution time. """
        s_time = time()
        print(f"Operation started.")
        getattr(self, self.operation)()
        print(f"Operation done in {time() - s_time:.1f} seconds.")
        return 0

    def analyze(self) -> None:
        """ Run the lexer in parallel on all translations and save the results. """
        results = self.engine_call("lexer_query_all", self._translations.items())
        self.engine_call("rules_save", results)

    def index(self) -> None:
        """ Run the loaded translations through the lexer and make an index of examples for each built-in rule. """
        self.engine_call(f"set_config_lexer:need_all_keys", True)
        index = self.engine_call("index_generate", self._translations.items())
        self.engine_call("index_save", index)

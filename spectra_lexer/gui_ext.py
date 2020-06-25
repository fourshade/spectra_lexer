from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.resource.translations import ExamplesDict, TranslationsDict, TranslationsIO
from spectra_lexer.search.engine import SearchEngine
from spectra_lexer.util.config import SimpleConfigDict


class GUIExtension:
    """ Layer for user GUI actions that may require disk access or other higher permissions. """

    def __init__(self, io:TranslationsIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 examples_path:str, cfg_path:str) -> None:
        self._io = io
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._examples_path = examples_path  # User examples index file path.
        self._config = SimpleConfigDict(cfg_path, "app_qt")
        self._last_translations = {}

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._last_translations = translations
        self._search_engine.set_translations(translations)

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = self._io.load_json_translations(*filenames)
        self.set_translations(translations)

    def set_examples(self, examples:ExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_examples(examples)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. """
        examples = self._io.load_json_examples(filename)
        self.set_examples(examples)

    def load_start_examples(self) -> None:
        """ Load the startup examples index. Ignore I/O errors since it may be missing. """
        try:
            self.load_examples(self._examples_path)
        except OSError:
            pass

    def compile_examples(self, size:int) -> None:
        """ Make an examples index, set it as active, and save it as JSON. """
        examples = self._analyzer.compile_index(self._last_translations.items(), size=size)
        self.set_examples(examples)
        self._io.save_json_examples(self._examples_path, examples)

    def load_config(self) -> None:
        self._config.read()

    def get_config(self) -> dict:
        return {**self._config}

    def update_config(self, options:dict) -> None:
        self._config.update(options)
        self._config.write()

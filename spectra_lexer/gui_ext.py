from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_resource import StenoResourceIO
from spectra_lexer.spc_search import ExamplesDict, SearchEngine, TranslationsDict


class GUIExtension:
    """ Layer for user GUI actions that may require disk access or other higher permissions. """

    def __init__(self, io:StenoResourceIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 translations_paths=(), examples_path="") -> None:
        self._io = io
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._translations_paths = translations_paths  # Starting translation file paths.
        self._examples_path = examples_path            # User examples index file path.
        self._last_translations = {}                   # Most recently loaded translations (for indexing).

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._search_engine.set_translations(translations)
        self._last_translations = translations

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

    def compile_examples(self, size:int) -> None:
        """ Make an examples index, set it as active, and save it as JSON. """
        examples = self._analyzer.compile_index(self._last_translations.items(), size=size)
        self.set_examples(examples)
        self._io.save_json_examples(self._examples_path, examples)

    def load_initial(self) -> None:
        """ Load optional startup resources. Ignore I/O errors since any of them may be missing. """
        if self._translations_paths:
            try:
                self.load_translations(*self._translations_paths)
            except OSError:
                pass
        if self._examples_path:
            try:
                self.load_examples(self._examples_path)
            except OSError:
                pass

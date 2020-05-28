from spectra_lexer.analysis import StenoAnalyzer, Translation, TranslationPairs
from spectra_lexer.display import BoardEngine, GraphEngine, RuleGraph
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search import ExamplesMap, MatchDict, SearchEngine, TranslationsMap
from spectra_lexer.translations import ExamplesDict, TranslationsDict, TranslationsIO


class StenoEngine:
    """ Top-level controller for all steno search, analysis, and display components. """

    def __init__(self, io:TranslationsIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 graph_engine:GraphEngine, board_engine:BoardEngine) -> None:
        self.io = io
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.graph_engine = graph_engine
        self.board_engine = board_engine
        self._translations = {}

    def set_translations(self, translations:TranslationsMap) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._translations = translations
        self.search_engine.set_translations(translations)

    def load_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = self.io.load_json_translations(*filenames)
        self.set_translations(translations)
        return translations

    def set_examples(self, examples:ExamplesMap) -> None:
        """ Send a new examples index dict to the search engine. """
        self.search_engine.set_examples(examples)

    def load_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file. """
        examples = self.io.load_json_examples(filename)
        self.set_examples(examples)
        return examples

    def search(self, pattern:str, count:int=None, mode_strokes=False) -> MatchDict:
        return self.search_engine.search(pattern, count, mode_strokes=mode_strokes)

    def search_regex(self, pattern:str, count:int=None, mode_strokes=False) -> MatchDict:
        return self.search_engine.search_regex(pattern, count, mode_strokes=mode_strokes)

    def search_examples(self, rule_id:str, pattern:str, count:int, mode_strokes=False) -> MatchDict:
        return self.search_engine.search_examples(rule_id, pattern, count, mode_strokes=mode_strokes)

    def has_examples(self, rule_id:str) -> bool:
        return self.search_engine.has_examples(rule_id)

    def random_example(self, rule_id:str) -> Translation:
        return self.search_engine.random_example(rule_id)

    def analyze(self, keys:str, letters:str, strict_mode=False) -> StenoRule:
        return self.analyzer.query(keys, letters, strict_mode=strict_mode)

    def best_translation(self, translations:TranslationPairs) -> Translation:
        return self.analyzer.best_translation(translations)

    def compile_examples(self, size:int=None, filename:str=None, process_count=0) -> None:
        """ Run the lexer on all translations with an optional <size> filter and look at the top-level rule IDs.
            Make a index with examples of every translation that used each built-in rule and set it as active.
            If a <filename> is given, save the index as JSON at the end. """
        translations = self._translations.items()
        index = self.analyzer.compile_index(translations, size=size, process_count=process_count)
        examples = {r_id: dict(pairs) for r_id, pairs in index.items()}
        self.set_examples(examples)
        if filename is not None:
            self.io.save_json_examples(filename, examples)

    def generate_board(self, rule:StenoRule, aspect_ratio:float=None, show_letters=True) -> str:
        return self.board_engine.draw_rule(rule, aspect_ratio, show_letters=show_letters)

    def generate_board_from_keys(self, keys:str, aspect_ratio:float=None) -> str:
        return self.board_engine.draw_keys(keys, aspect_ratio)

    def generate_graph(self, rule:StenoRule, compressed=True, compat=False) -> RuleGraph:
        return self.graph_engine.graph(rule, compressed=compressed, compat=compat)

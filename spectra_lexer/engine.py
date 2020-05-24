import json

from spectra_lexer.analysis import StenoAnalyzer, Translation, TranslationFilter, TranslationPairs
from spectra_lexer.display import BoardFactory, GraphFactory, RuleGraph
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search import ExamplesMap, MatchDict, SearchEngine, TranslationsMap


def json_load_dict(filename:str) -> dict:
    """ Load a string dict from a JSON file. UTF-8 is explicitly required for some strings. """
    with open(filename, 'r', encoding='utf-8') as fp:
        return json.load(fp)


def json_dump_dict(filename:str, d:dict) -> None:
    """ Save a string dict to a JSON file. Key sorting helps some algorithms run faster.
        ensure_ascii=False is required to preserve Unicode symbols. """
    with open(filename, 'w', encoding='utf-8') as fp:
        json.dump(d, fp, sort_keys=True, ensure_ascii=False)


class StenoEngine:
    """ Top-level controller for all steno search, analysis, and display components. """

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 node_factory:GraphFactory, board_factory:BoardFactory) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_factory = node_factory
        self._board_factory = board_factory
        self._translations = {}

    def set_translations(self, translations:TranslationsMap) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._translations = translations
        self._search_engine.set_translations(translations)

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            if filename.endswith(".json"):
                d = json_load_dict(filename)
                if not isinstance(d, dict):
                    raise TypeError(f'Steno translations file "{filename}" does not contain a dictionary.')
                translations.update(d)
        self.set_translations(translations)

    def set_examples(self, examples:ExamplesMap) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_examples(examples)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. """
        examples = json_load_dict(filename)
        if not isinstance(examples, dict) or not all([isinstance(v, dict) for v in examples.values()]):
            raise TypeError(f'Examples index file "{filename}" does not contain a dict of dicts.')
        self.set_examples(examples)

    def search(self, pattern:str, count:int=None, mode_strokes=False) -> MatchDict:
        return self._search_engine.search(pattern, count, mode_strokes=mode_strokes)

    def search_regex(self, pattern:str, count:int=None, mode_strokes=False) -> MatchDict:
        return self._search_engine.search_regex(pattern, count, mode_strokes=mode_strokes)

    def search_examples(self, rule_id:str, pattern:str, count:int, mode_strokes=False) -> MatchDict:
        return self._search_engine.search_examples(rule_id, pattern, count, mode_strokes=mode_strokes)

    def has_examples(self, rule_id:str) -> bool:
        return self._search_engine.has_examples(rule_id)

    def random_example(self, rule_id:str) -> Translation:
        return self._search_engine.random_example(rule_id)

    def analyze(self, keys:str, letters:str, strict_mode=False) -> StenoRule:
        return self._analyzer.query(keys, letters, strict_mode=strict_mode)

    def best_translation(self, translations:TranslationPairs) -> Translation:
        return self._analyzer.best_translation(translations)

    def compile_examples(self, size:int=None, filename:str=None, process_count=0) -> None:
        """ Run the lexer on all translations with an optional <size> filter and look at the top-level rule IDs.
            Make a index with examples of every translation that used each built-in rule and set it as active.
            If a <filename> is given, save the index as JSON at the end. """
        translations = self._translations.items()
        index = self._analyzer.compile_index(translations, size=size, process_count=process_count)
        examples = {r_id: dict(pairs) for r_id, pairs in index.items()}
        self.set_examples(examples)
        if filename is not None:
            json_dump_dict(filename, examples)

    def generate_board(self, rule:StenoRule, aspect_ratio:float=None, show_letters=True) -> str:
        return self._board_factory.board_from_rule(rule, aspect_ratio, show_letters=show_letters)

    def generate_board_from_keys(self, keys:str, aspect_ratio:float=None) -> str:
        return self._board_factory.board_from_keys(keys, aspect_ratio)

    def generate_graph(self, rule:StenoRule, compressed=True, compat=False) -> RuleGraph:
        return self._graph_factory.build(rule, compressed=compressed, compat=compat)

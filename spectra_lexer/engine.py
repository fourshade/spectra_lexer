import random
from types import SimpleNamespace
from typing import List, Sequence

from spectra_lexer import Spectra
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.resource.translations import ExamplesDict, Translation, TranslationsDict, TranslationFilter
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_graph import GraphEngine, GraphTree, HTMLGraph
from spectra_lexer.spc_lexer import StenoAnalyzer
from spectra_lexer.spc_resource import StenoResourceIO
from spectra_lexer.spc_search import MatchDict, SearchEngine


class EngineOptions(SimpleNamespace):
    """ Namespace for all runtime engine options. """

    search_mode_strokes: bool = False       # If True, search for strokes instead of translations.
    search_mode_regex: bool = False         # If True, perform search using regex characters.
    search_match_limit: int = 100           # Maximum number of matches returned on one page of a search.
    lexer_strict_mode: bool = False         # Only return lexer results that match every key in a translation.
    board_aspect_ratio: float = None        # Aspect ratio for board viewing area (None means pure horizontal layout).
    board_show_compound: bool = True        # Show compound keys on board with alt labels (i.e. F instead of TP).
    board_show_letters: bool = True         # Show letters on board when possible. Letters override alt labels.
    graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
    graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.


class Engine:
    """ Main layer for executing common user actions. """

    _analysis: StenoRule  # Current analysis.
    _graph: GraphTree     # Graph of current analysis.
    _ref: str             # Most recently selected graph node reference.

    def __init__(self, io:StenoResourceIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 graph_engine:GraphEngine, board_engine:BoardEngine, translations_paths=(), examples_path="") -> None:
        self._io = io
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_engine = graph_engine
        self._board_engine = board_engine
        self._translations_paths = translations_paths  # Starting translation file paths.
        self._examples_path = examples_path            # User examples index file path.
        self._opts = EngineOptions()                   # Current user options.
        self._translations = {}                        # Currently loaded translations (for indexing).
        self.run_query("", "")                         # Start with a valid (dummy) analysis state.

    def set_options(self, options:dict) -> None:
        """ Replace all <options> at once. """
        self._opts = EngineOptions(**options)

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._search_engine.set_translations(translations)
        self._translations = translations

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

    def compile_examples(self, filt:TranslationFilter=None) -> None:
        """ Make an examples index for the current translations with an optional <filt>er.
            Set the new index as active and save it as JSON. """
        pairs = self._translations.items()
        if filt is not None:
            pairs = filt.filter(pairs)
        examples = self._analyzer.compile_index(pairs)
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

    def search(self, pattern:str, pages=1) -> MatchDict:
        """ Perform a search based on the current options. """
        count = pages * self._opts.search_match_limit
        mode_strokes = self._opts.search_mode_strokes
        mode_regex = self._opts.search_mode_regex
        return self._search_engine.search(pattern, count, mode_strokes=mode_strokes, mode_regex=mode_regex)

    def random_pattern(self, example_id:str) -> str:
        """ Return a valid example search pattern for <example_id> centered on a random translation if one exists. """
        mode_strokes = self._opts.search_mode_strokes
        return self._search_engine.random_pattern(example_id, mode_strokes=mode_strokes)

    def best_translation(self, match:str, mappings:Sequence[str]) -> Translation:
        """ Return the best translation in a match-mappings pair from search. """
        if self._opts.search_mode_strokes:
            # There can only be one mapping in strokes mode.
            keys = match
            letters = mappings[0]
        else:
            keys = self._analyzer.best_translation(mappings, match)
            letters = match
        return keys, letters

    def random_translation(self, matches:MatchDict) -> Translation:
        """ Return a translation randomly chosen from <matches>. """
        assert matches
        match = random.choice(list(matches))
        mappings = matches[match]
        return self.best_translation(match, mappings)

    def search_selection(self, keys:str, letters:str) -> List[str]:
        return [keys, letters] if self._opts.search_mode_strokes else [letters, keys]

    def run_query(self, keys:str, letters:str) -> None:
        """ Run a lexer analysis and build a node graph of every rule in it recursively. """
        self._analysis = self._analyzer.query(keys, letters, strict_mode=self._opts.lexer_strict_mode)
        self._graph = self._graph_engine.graph(self._analysis, compressed=self._opts.graph_compressed_layout)
        self._ref = ""

    def get_refs(self) -> List[str]:
        """ Return a list of all valid graph node reference strings. """
        return list(self._graph)

    def select_ref(self, ref:str) -> None:
        """ Choose a graph node by reference as the current display target. """
        self._ref = ref

    def _current_rule(self) -> StenoRule:
        """ Get the current node's rule, or the root analysis by default. """
        return self._graph.get(self._ref, self._analysis)

    def get_caption(self) -> str:
        """ Generate a caption for the current rule. The root analysis caption shows its reliability.
            Others show the keys and info string. Rules with children show the complete mapping of keys to letters. """
        rule = self._current_rule()
        rulemap = rule.rulemap
        if rule is self._analysis:
            if not any(item.child.is_unmatched for item in rulemap):
                return 'Found complete match.'
            if len(rulemap) == 1:
                return 'No matches found.'
            return 'Incomplete match. Not reliable.'
        keys = rule.keys
        letters = rule.letters
        info = rule.info
        if rulemap and letters:
            return f'{keys} → {letters}: {info}'
        return f'{keys}: {info}'

    def draw_graph(self, *, intense=False) -> HTMLGraph:
        """ Generate an HTML text graph for the current rule. """
        return self._graph.draw(self._ref, intense=intense, compat=self._opts.graph_compatibility_mode)

    def draw_board(self) -> BoardDiagram:
        """ Generate a board diagram for the current rule. """
        rule = self._current_rule()
        aspect_ratio = self._opts.board_aspect_ratio
        if self._opts.board_show_compound:
            board = self._board_engine.draw_rule(rule, aspect_ratio, show_letters=self._opts.board_show_letters)
        else:
            board = self._board_engine.draw_keys(rule.keys, aspect_ratio)
        return board

    def get_example_id(self) -> str:
        """ Return a rule ID usable in an example link, but only if the current rule actually has examples. """
        rule = self._current_rule()
        r_id = rule.id
        if not self._search_engine.has_examples(r_id):
            r_id = ""
        return r_id

    def find_ref(self, example_id:str) -> str:
        """ Return the first reference to a node with a specific rule ID, if one exists. """
        for ref, rule in self._graph.items():
            if example_id == rule.id:
                return ref
        return ""


def build_engine(spectra:Spectra) -> Engine:
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    translations_paths = spectra.translations_paths
    index_path = spectra.index_path
    return Engine(io, search_engine, analyzer, graph_engine, board_engine, translations_paths, index_path)

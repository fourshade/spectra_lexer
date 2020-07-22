import random
from typing import List, Sequence

from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.spc_board import BoardDiagram, BoardEngine
from spectra_lexer.spc_graph import GraphEngine, HTMLGraph
from spectra_lexer.spc_lexer import StenoAnalyzer, Translation
from spectra_lexer.spc_search import MatchDict, SearchEngine


class GUIOptions:
    """ Namespace for all GUI-related steno engine options. """

    search_mode_strokes: bool = False       # If True, search for strokes instead of translations.
    search_mode_regex: bool = False         # If True, perform search using regex characters.
    search_match_limit: int = 100           # Maximum number of matches returned on one page of a search.
    lexer_strict_mode: bool = False         # Only return lexer results that match every key in a translation.
    board_aspect_ratio: float = None        # Aspect ratio for board viewing area (None means pure horizontal layout).
    board_show_compound: bool = True        # Show compound keys on board with alt labels (i.e. F instead of TP).
    board_show_letters: bool = True         # Show letters on board when possible. Letters override alt labels.
    graph_compressed_layout: bool = True    # Compress the graph layout vertically to save space.
    graph_compatibility_mode: bool = False  # Force correct spacing in the graph using HTML tables.

    # These user options should be saved in a CFG file.
    CFG_OPTIONS = [("search_match_limit", "Match Limit",
                    "Maximum number of matches returned on one page of a search."),
                   ("lexer_strict_mode", "Strict Mode",
                    "Only return lexer results that match every key in a translation."),
                   ("graph_compressed_layout", "Compressed Layout",
                    "Compress the graph layout vertically to save space.")]

    def __init__(self, options:dict=None) -> None:
        """ Update option attributes from an input dict. """
        if options is not None:
            self.__dict__.update(options)


class GUIEngine:
    """ Layer for executing common user GUI actions. """

    def __init__(self, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 graph_engine:GraphEngine, board_engine:BoardEngine) -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_engine = graph_engine
        self._board_engine = board_engine
        self._opts = GUIOptions()  # Current user options.
        empty_graph = graph_engine.graph(analyzer.query("", ""))
        self._graph = empty_graph  # Graph of current analysis.

    def set_options(self, opts:GUIOptions) -> None:
        self._opts = opts

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

    def random_translation(self, matches:MatchDict) -> Translation:
        """ Return a translation randomly chosen from <matches>. """
        assert matches
        match = random.choice(list(matches))
        mapping = matches[match][0]
        if self._opts.search_mode_strokes:
            return match, mapping
        else:
            return mapping, match

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

    def _analyze(self, keys:str, letters:str) -> StenoRule:
        return self._analyzer.query(keys, letters, strict_mode=self._opts.lexer_strict_mode)

    def _build_graph(self, analysis:StenoRule) -> None:
        """ Build a node graph of every rule in <analysis> and store it. """
        self._graph = self._graph_engine.graph(analysis, compressed=self._opts.graph_compressed_layout,
                                               compat=self._opts.graph_compatibility_mode)

    def query(self, keys:str, letters:str) -> List[str]:
        analysis = self._analyze(keys, letters)
        self._build_graph(analysis)
        return list(self._graph)

    def get_caption(self, ref="") -> str:
        return self._graph.caption(ref)

    def draw_graph(self, ref="", intense=False) -> HTMLGraph:
        return self._graph.draw(ref, intense=intense)

    def draw_board(self, ref="") -> BoardDiagram:
        rule = self._graph[ref]
        aspect_ratio = self._opts.board_aspect_ratio
        if self._opts.board_show_compound:
            board = self._board_engine.draw_rule(rule, aspect_ratio, show_letters=self._opts.board_show_letters)
        else:
            board = self._board_engine.draw_keys(rule.keys, aspect_ratio)
        return board

    def get_example_id(self, ref="") -> str:
        """ Return a rule ID usable in an example link, but only for rules that actually have examples. """
        rule = self._graph[ref]
        r_id = rule.id
        if not self._search_engine.has_examples(r_id):
            r_id = ""
        return r_id

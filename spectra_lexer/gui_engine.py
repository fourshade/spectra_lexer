from typing import Dict, Iterable, Optional

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.display import BoardDiagram, BoardEngine, GraphEngine, GraphTree, HTMLGraph
from spectra_lexer.resource.rules import StenoRule
from spectra_lexer.search.engine import MatchDict, SearchEngine


class SearchResults:
    """ Data class for all results of a search. """

    def __init__(self, matches:MatchDict, is_complete=True) -> None:
        self.matches = matches          # Dict of matched strings with a list of mappings for each.
        self.is_complete = is_complete  # If True, this includes all available results.


class DisplayPage:
    """ Data class that contains an HTML formatted graph, a caption, an SVG board, and a rule ID reference. """

    def __init__(self, graph:HTMLGraph, intense_graph:HTMLGraph, caption:str, board:BoardDiagram, rule_id="") -> None:
        self.graph = graph                  # HTML graph text for this selection.
        self.intense_graph = intense_graph  # Brighter HTML text graph for this selection.
        self.caption = caption              # Text characters drawn as a caption (possibly on a tooltip).
        self.board = board                  # XML string containing this rule's SVG board diagram.
        self.rule_id = rule_id              # If the selection uses a valid rule, its rule ID, else an empty string.


class DisplayData:
    """ Data class that contains graphical data for an entire analysis. """

    def __init__(self, keys:str, letters:str, pages:Dict[str, DisplayPage], default_page:DisplayPage) -> None:
        self.keys = keys                  # Translation keys in RTFCRE.
        self.letters = letters            # Translation letters.
        self.pages_by_ref = pages         # Analysis pages keyed by HTML anchor reference.
        self.default_page = default_page  # Default starting analysis page. May also be included in pages_by_ref.


class GUIOutput:
    """ Data class that contains an entire GUI update. All fields are optional. """

    def __init__(self, search_input:str=None, search_results:SearchResults=None, display_data:DisplayData=None) -> None:
        self.search_input = search_input      # Product of an example search action.
        self.search_results = search_results  # Product of a search action.
        self.display_data = display_data      # Product of a query action.


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
                 graph_engine:GraphEngine, board_engine:BoardEngine, *, index_delim=";") -> None:
        self._search_engine = search_engine
        self._analyzer = analyzer
        self._graph_engine = graph_engine
        self._board_engine = board_engine
        self._index_delim = index_delim  # Delimiter between rule name and query for example index searches.
        self._opts = GUIOptions()        # Current user options.

    def set_options(self, opts:GUIOptions) -> None:
        self._opts = opts

    def _search(self, pattern:str, pages:int) -> SearchResults:
        """ Perform a search based on the current options and/or presence of the index delimiter. """
        count = pages * self._opts.search_match_limit
        mode_strokes = self._opts.search_mode_strokes
        se = self._search_engine
        if not pattern or pattern.isspace():
            matches = {}
            is_complete = True
        elif self._index_delim in pattern:
            link_ref, rule_pattern = pattern.split(self._index_delim, 1)
            matches = se.search_examples(link_ref, rule_pattern, count, mode_strokes=mode_strokes)
            is_complete = True
        else:
            method = se.search_regex if self._opts.search_mode_regex else se.search
            matches = method(pattern, count, mode_strokes=mode_strokes)
            is_complete = len(matches) < count
        return SearchResults(matches, is_complete)

    def _analyze(self, keys:str, letters:str) -> StenoRule:
        return self._analyzer.query(keys, letters, strict_mode=self._opts.lexer_strict_mode)

    def _build_graph(self, analysis:StenoRule) -> GraphTree:
        return self._graph_engine.graph(analysis, compressed=self._opts.graph_compressed_layout,
                                        compat=self._opts.graph_compatibility_mode)

    def _draw_board(self, rule:StenoRule) -> BoardDiagram:
        aspect_ratio = self._opts.board_aspect_ratio
        if self._opts.board_show_compound:
            board = self._board_engine.draw_rule(rule, aspect_ratio, show_letters=self._opts.board_show_letters)
        else:
            board = self._board_engine.draw_keys(rule.keys, aspect_ratio)
        return board

    def _build_page(self, ngraph:HTMLGraph, igraph:HTMLGraph, rule:StenoRule) -> DisplayPage:
        """ Create a display page for a rule selection. Do not add links to rules for which we don't have examples. """
        caption = rule.info
        board = self._draw_board(rule)
        r_id = rule.id
        if not self._search_engine.has_examples(r_id):
            r_id = ""
        return DisplayPage(ngraph, igraph, caption, board, r_id)

    def _display(self, analysis:StenoRule) -> DisplayData:
        """ Return a full set of display data for a steno analysis, including all possible selections. """
        graph = self._build_graph(analysis)
        pages = {}
        for ref, rule in graph.iter_mappings():
            ngraph = graph.draw(ref)
            igraph = graph.draw(ref, intense=True)
            pages[ref] = self._build_page(ngraph, igraph, rule)
        # When nothing is selected, use the board and caption for the root node.
        default_graph = graph.draw()
        default_page = self._build_page(default_graph, default_graph, analysis)
        return DisplayData(analysis.keys, analysis.letters, pages, default_page)

    def _check_query(self, keys:str, letters:str) -> Optional[DisplayData]:
        if keys and letters:
            analysis = self._analyze(keys, letters)
            return self._display(analysis)

    def query(self, keys:Iterable[str], letters:str) -> GUIOutput:
        """ Execute and return a full display of a lexer query.
            <keys> may be either a single string or an iterable of strings. """
        if not isinstance(keys, str):
            keys_seq = list(filter(None, keys))
            keys = self._analyzer.best_translation(keys_seq, letters) if keys_seq else ""
        display = self._check_query(keys, letters)
        return GUIOutput(display_data=display)

    def search(self, pattern:str, pages=1) -> GUIOutput:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        results = self._search(pattern, pages)
        return GUIOutput(search_results=results)

    def search_examples(self, link_ref:str) -> GUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one at random.
            Overwrite the current search input with its pattern. """
        keys, letters = self._search_engine.random_example(link_ref)
        display = self._check_query(keys, letters)
        if display is None:
            return GUIOutput()
        match = keys if self._opts.search_mode_strokes else letters
        pattern = link_ref + self._index_delim + match
        results = self._search(pattern, 1)
        return GUIOutput(search_input=pattern, search_results=results, display_data=display)

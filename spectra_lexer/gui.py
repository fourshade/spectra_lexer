from typing import Dict

from spectra_lexer.analysis import Translation
from spectra_lexer.engine import StenoEngine
from spectra_lexer.search import MatchDict, SearchRegexError


class SearchResults:
    """ Data class for all results of a search. """

    def __init__(self, matches:MatchDict, is_complete=True) -> None:
        self.matches = matches          # Dict of matched strings with a list of mappings for each.
        self.is_complete = is_complete  # If True, this includes all available results.


class DisplayPage:
    """ Data class that contains an HTML formatted graph, a caption, an SVG board, and a rule ID reference. """

    def __init__(self, graph:str, intense_graph:str, caption:str, board:str, rule_id="") -> None:
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


class GUILayer:
    """ Layer for common user GUI actions. """

    def __init__(self, engine:StenoEngine, *, index_delim=";") -> None:
        self._engine = engine            # Main steno analysis engine.
        self._index_delim = index_delim  # Delimiter between rule name and query for example index searches.
        self._opts = GUIOptions()        # Current user options.

    def set_options(self, opts:GUIOptions) -> None:
        self._opts = opts

    def _search(self, pattern:str, pages:int) -> SearchResults:
        count = pages * self._opts.search_match_limit
        mode_strokes = self._opts.search_mode_strokes
        if self._index_delim in pattern:
            link_ref, pattern = pattern.split(self._index_delim, 1)
            matches = self._engine.search_examples(link_ref, pattern, count, mode_strokes=mode_strokes)
            is_complete = True
        else:
            try:
                method = self._engine.search_regex if self._opts.search_mode_regex else self._engine.search
                matches = method(pattern, count, mode_strokes=mode_strokes)
                is_complete = len(matches) < count
            except SearchRegexError:
                matches = {"REGEX ERROR": []}
                is_complete = True
        return SearchResults(matches, is_complete)

    def _analyze(self, keys:str, letters:str) -> DisplayData:
        opts = self._opts
        analysis = self._engine.analyze(keys, letters, strict_mode=opts.lexer_strict_mode)
        graph = self._engine.generate_graph(analysis, compressed=opts.graph_compressed_layout,
                                            compat=opts.graph_compatibility_mode)
        pages = {}
        default_page = None
        for ref in graph.refs():
            ngraph = graph.draw(ref)
            igraph = graph.draw(ref, intense=True)
            rule = graph.get_rule(ref)
            caption = rule.info
            aspect_ratio = opts.board_aspect_ratio
            if opts.board_show_compound:
                board = self._engine.generate_board(rule, aspect_ratio, show_letters=opts.board_show_letters)
            else:
                board = self._engine.generate_board_from_keys(rule.keys, aspect_ratio)
            # Remove links to any rules for which we don't have examples.
            r_id = rule.id if self._engine.has_examples(rule.id) else ""
            pages[ref] = DisplayPage(ngraph, igraph, caption, board, r_id)
            if rule is analysis:
                # When nothing is selected, use the board and caption for the root node.
                default_graph = graph.draw()
                default_page = DisplayPage(default_graph, default_graph, caption, board)
        return DisplayData(keys, letters, pages, default_page)

    def query(self, translation:Translation, *others:Translation) -> GUIOutput:
        """ Execute and display a graph of a lexer query from search results or user strokes. """
        keys, letters = self._engine.best_translation([translation, *others]) if others else translation
        output = GUIOutput()
        output.display_data = self._analyze(keys, letters)
        return output

    def search(self, pattern:str, pages=1) -> GUIOutput:
        """ Do a new search and return results unless the input is blank. """
        output = GUIOutput()
        if pattern.strip():
            output.search_results = self._search(pattern, pages)
        return output

    def search_examples(self, link_ref:str) -> GUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one at random.
            Overwrite the current search input with its pattern. """
        output = GUIOutput()
        keys, letters = self._engine.random_example(link_ref)
        if keys and letters:
            match = keys if self._opts.search_mode_strokes else letters
            pattern = link_ref + self._index_delim + match
            output.search_input = pattern
            output.search_results = self._search(pattern, 1)
            output.display_data = self._analyze(keys, letters)
        return output

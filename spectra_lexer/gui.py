from typing import Any, Dict, Tuple

from spectra_lexer.engine import StenoEngine
from spectra_lexer.search import SearchResults


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

    search_input: str = None              # Product of an example search action.
    search_results: SearchResults = None  # Product of a search action.
    display_data: DisplayData = None      # Product of a query action.


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

    def __init__(self, *opt_dicts:Dict[str, Any]) -> None:
        """ Update option attributes from input dicts in order. """
        for d in opt_dicts:
            self.__dict__.update(d)


class GUILayer:
    """ Layer for common user GUI actions. """

    def __init__(self, engine:StenoEngine) -> None:
        self._engine = engine  # Main steno analysis engine.

    def query(self, translation:Tuple[str, str], *others:Tuple[str, str], opts=GUIOptions()) -> GUIOutput:
        """ Execute and display a graph of a lexer query from search results or user strokes. """
        output = GUIOutput()
        strict_mode = opts.lexer_strict_mode
        if others:
            translation = self._engine.best_translation(translation, *others)
        analysis = self._engine.analyze(*translation, strict_mode=strict_mode)
        compressed = opts.graph_compressed_layout
        compat = opts.graph_compatibility_mode
        graph = self._engine.generate_graph(analysis, compressed, compat)
        aspect_ratio = opts.board_aspect_ratio
        show_compound = opts.board_show_compound
        show_letters = opts.board_show_letters
        pages = {}
        root_ref = None
        for ref in graph.refs():
            ngraph = graph.draw(ref)
            igraph = graph.draw(ref, intense=True)
            rule = graph.get_rule(ref)
            # Make a caption to display above the board diagram for this rule.
            if rule is analysis:
                # The root translation is in the title bar. Show only the info string in its caption.
                caption = rule.info
                root_ref = ref
            elif rule and rule.letters:
                # Compound rules show the complete mapping of keys to letters in their caption.
                caption = f'{rule}: {rule.info}'
            else:
                # Base rules display only their keys to the left of their descriptions.
                caption = f"{rule.keys}: {rule.info}"
            if show_compound:
                board = self._engine.generate_board(rule, aspect_ratio, show_letters)
            else:
                board = self._engine.generate_board_from_keys(rule.keys, aspect_ratio)
            # Remove links to any rules for which we don't have examples.
            r_id = rule.id if self._engine.has_examples(rule.id) else ""
            pages[ref] = DisplayPage(ngraph, igraph, caption, board, r_id)
        # When nothing is selected, use the board and caption for the root node.
        root_page = pages[root_ref]
        default_graph = graph.draw()
        default_page = DisplayPage(default_graph, default_graph, root_page.caption, root_page.board)
        output.display_data = DisplayData(analysis.keys, analysis.letters, pages, default_page)
        return output

    def search(self, pattern:str, pages=1, *, opts=GUIOptions()) -> GUIOutput:
        """ Do a new search and return results unless the input is blank. """
        output = GUIOutput()
        mode_strokes = opts.search_mode_strokes
        if pattern.strip():
            count = pages * opts.search_match_limit
            output.search_results = self._engine.search(pattern, count, mode_strokes, opts.search_mode_regex)
        return output

    def search_examples(self, link_ref:str, *, opts=GUIOptions()) -> GUIOutput:
        """ When a link is clicked, search for examples of the named rule and select one. """
        mode_strokes = opts.search_mode_strokes
        keys, letters, pattern = self._engine.random_example(link_ref, mode_strokes)
        if keys and letters:
            output = self.query((keys, letters), opts=opts)
            output.search_input = pattern
            output.search_results = self._engine.search(pattern, opts.search_match_limit, mode_strokes)
        else:
            output = GUIOutput()
        return output

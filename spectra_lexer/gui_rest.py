from threading import Lock
from typing import Dict, Iterable, Sequence

from spectra_lexer.gui_engine import GUIEngine, GUIOptions
from spectra_lexer.spc_board import BoardDiagram
from spectra_lexer.spc_graph import HTMLGraph
from spectra_lexer.spc_search import MatchDict


class RESTDisplayPage:
    """ Data class that contains two HTML formatted graphs, a caption, an SVG board, and a rule ID reference. """

    def __init__(self, graph:HTMLGraph, intense_graph:HTMLGraph, caption:str, board:BoardDiagram, rule_id="") -> None:
        self.graph = graph                  # HTML graph text for this selection.
        self.intense_graph = intense_graph  # Brighter HTML text graph for this selection.
        self.caption = caption              # Text characters drawn as a caption (possibly on a tooltip).
        self.board = board                  # XML string containing this rule's SVG board diagram.
        self.rule_id = rule_id              # If the selection uses a valid rule, its rule ID, else an empty string.


class RESTDisplay:
    """ Data class that contains graphical data for an entire analysis. """

    def __init__(self, keys:str, letters:str, pages:Dict[str, RESTDisplayPage], default_page:RESTDisplayPage) -> None:
        self.keys = keys                  # Translation keys in RTFCRE.
        self.letters = letters            # Translation letters.
        self.pages_by_ref = pages         # Analysis pages keyed by HTML anchor reference.
        self.default_page = default_page  # Default starting analysis page. May also be included in pages_by_ref.


class RESTUpdates:
    """ Data class for a set of REST GUI updates. All fields are optional. """

    def __init__(self, matches:MatchDict=None, display:RESTDisplay=None) -> None:
        self.matches = matches  # New items in the search lists.
        self.display = display  # New graphical objects.


class RESTGUIApplication:
    """ Thread-safe GUI application for use in a web server.
        Steno rules may be parsed into a tree of nodes, each of which may have several forms of representation.
        All information for a single node is combined into a display "page" which can be used for GUI updates.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer HTTP requests and more opportunities for caching. """

    def __init__(self, engine:GUIEngine) -> None:
        self._engine = engine
        self._lock = Lock()

    def run(self, action:str, args:Iterable=(), options:dict=None) -> RESTUpdates:
        """ Perform a REST app action. Input data includes an action method, its arguments (if any), and GUI options.
            Option and graph state is not thread-safe, so we need a lock. """
        opts = GUIOptions(options)
        with self._lock:
            self._engine.set_options(opts)
            method = getattr(self, "REST_" + action)
            updates = method(*args)
            return RESTUpdates(**updates)

    def _draw_page(self, ref="") -> RESTDisplayPage:
        """ Create a display page for a rule <ref>erence, or a default page if ref is empty or invalid. """
        ngraph = self._engine.draw_graph(ref)
        igraph = self._engine.draw_graph(ref, intense=True)
        caption = self._engine.get_caption(ref)
        board = self._engine.draw_board(ref)
        r_id = self._engine.get_example_id(ref)
        return RESTDisplayPage(ngraph, igraph, caption, board, r_id)

    def _display(self, keys:str, letters:str) -> RESTDisplay:
        """ Run a query and return a full set of display data, including all possible selections. """
        refs = self._engine.query(keys, letters)
        pages = {ref: self._draw_page(ref) for ref in refs}
        default_page = self._draw_page()
        return RESTDisplay(keys, letters, pages, default_page)

    def REST_search(self, pattern:str, pages=1) -> dict:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        return {"matches": self._engine.search(pattern, pages)}

    def REST_query(self, keys:str, letters:str) -> dict:
        """ Execute and return a full display of a lexer query. """
        return {"display": self._display(keys, letters)}

    def REST_query_match(self, match:str, mappings:Sequence[str]) -> dict:
        """ Query and display the best translation in a match-mappings pair from search. """
        keys, letters = self._engine.best_translation(match, mappings)
        return {"display": self._display(keys, letters)}

    def REST_search_examples(self, link_ref:str) -> dict:
        """ Search for examples of the named rule and display one at random. """
        pattern = self._engine.random_pattern(link_ref)
        if not pattern:
            return {}
        matches = self._engine.search(pattern)
        keys, letters = self._engine.random_translation(matches)
        return {"matches": matches, "display": self._display(keys, letters)}

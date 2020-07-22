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


class RESTUpdate:
    """ Data class that contains an entire REST GUI update. All fields are optional. """

    def __init__(self, search_results:MatchDict=None, display_data:RESTDisplay=None) -> None:
        self.search_results = search_results  # Product of a search action.
        self.display_data = display_data      # Product of a query action.


class RESTGUIApplication:
    """ Thread-safe GUI application for use in a web server.
        Steno rules may be parsed into a tree of nodes, each of which may have several forms of representation.
        All information for a single node is combined into a display "page" which can be used for GUI updates.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer HTTP requests and more opportunities for caching. """

    def __init__(self, gui:GUIEngine) -> None:
        self._gui = gui
        self._lock = Lock()

    def run(self, action:str, args:Iterable=(), options:dict=None) -> RESTUpdate:
        """ Perform a REST app action. Input data includes an action method, its arguments (if any), and GUI options.
            Option and graph state is not thread-safe, so we need a lock. """
        opts = GUIOptions(options)
        with self._lock:
            self._gui.set_options(opts)
            method = getattr(self, "REST_" + action)
            return method(*args)

    def _draw_page(self, ref="") -> RESTDisplayPage:
        """ Create a display page for a rule <ref>erence, or a default page if ref is empty or invalid. """
        ngraph = self._gui.draw_graph(ref)
        igraph = self._gui.draw_graph(ref, intense=True)
        caption = self._gui.get_caption(ref)
        board = self._gui.draw_board(ref)
        r_id = self._gui.get_example_id(ref)
        return RESTDisplayPage(ngraph, igraph, caption, board, r_id)

    def _display(self, keys:str, letters:str) -> RESTDisplay:
        """ Run a query and return a full set of display data, including all possible selections. """
        refs = self._gui.query(keys, letters)
        pages = {ref: self._draw_page(ref) for ref in refs}
        default_page = self._draw_page()
        return RESTDisplay(keys, letters, pages, default_page)

    def REST_search(self, pattern:str, pages=1) -> RESTUpdate:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        search_results = self._gui.search(pattern, pages)
        return RESTUpdate(search_results=search_results)

    def REST_query(self, keys:str, letters:str) -> RESTUpdate:
        """ Execute and return a full display of a lexer query. """
        display_data = self._display(keys, letters)
        return RESTUpdate(display_data=display_data)

    def REST_query_match(self, match:str, mappings:Sequence[str]) -> RESTUpdate:
        """ Query and display the best translation in a match-mappings pair from search. """
        keys, letters = self._gui.best_translation(match, mappings)
        return self.REST_query(keys, letters)

    def REST_search_examples(self, link_ref:str) -> RESTUpdate:
        """ Search for examples of the named rule and display one at random. """
        pattern = self._gui.random_pattern(link_ref)
        if not pattern:
            search_results = display_data = None
        else:
            search_results = self._gui.search(pattern)
            keys, letters = self._gui.random_translation(search_results)
            display_data = self._display(keys, letters)
        return RESTUpdate(search_results=search_results, display_data=display_data)

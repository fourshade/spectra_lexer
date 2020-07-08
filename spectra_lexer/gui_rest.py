from threading import Lock
from typing import Dict, Iterable

from spectra_lexer.gui_engine import GUIEngine, GUIOptions, QueryResults, SearchResults
from spectra_lexer.spc_board import BoardDiagram
from spectra_lexer.spc_graph import HTMLGraph


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

    def __init__(self, search_results:SearchResults=None, display_data:RESTDisplay=None) -> None:
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

    def _display(self, query_results:QueryResults) -> RESTDisplay:
        """ Return a full set of display data for a query, including all possible selections. """
        pages = {ref: self._draw_page(ref) for ref in query_results.refs}
        default_page = self._draw_page()
        return RESTDisplay(query_results.keys, query_results.letters, pages, default_page)

    def REST_search(self, pattern:str, pages=1) -> RESTUpdate:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        search_results = self._gui.search(pattern, pages)
        return RESTUpdate(search_results=search_results)

    def REST_query(self, keys:Iterable[str], letters:str) -> RESTUpdate:
        """ Execute and return a full display of a lexer query. """
        query_results = self._gui.query(keys, letters)
        display_data = self._display(query_results)
        return RESTUpdate(display_data=display_data)

    def REST_search_examples(self, link_ref:str) -> RESTUpdate:
        """ When a link is clicked, search for examples of the named rule and select one at random. """
        pattern = self._gui.random_pattern(link_ref)
        if not pattern:
            search_results = display_data = None
        else:
            search_results = self._gui.search(pattern)
            query_results = self._gui.query_random(search_results)
            display_data = self._display(query_results)
        return RESTUpdate(search_results=search_results, display_data=display_data)

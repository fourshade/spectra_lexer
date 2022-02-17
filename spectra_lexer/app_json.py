from typing import Dict, Sequence

from spectra_lexer import Spectra
from spectra_lexer.engine import Engine, build_engine
from spectra_lexer.http.json import JSONApplication, JSONDict, JSONList, JSONStruct
from spectra_lexer.spc_board import BoardDiagram
from spectra_lexer.spc_graph import HTMLGraph
from spectra_lexer.spc_search import EXPAND_KEY, MatchDict


class Request(JSONStruct):
    """ Contains all information from a JSON web request. """

    action: str               # Name of an action method to call.
    args: JSONList            # Positional arguments for the method.
    options: JSONDict = None  # GUI engine options to set before calling the method.


class Matches(JSONStruct):
    """ Contains results for the search lists. """

    pattern: str        # Input pattern string.
    results: MatchDict  # Dictionary of matched strings and each of their translation mappings.
    can_expand: bool    # If True, a search with more pages may yield more items.


class Selections(JSONStruct):
    """ Contains a specific selection in the search lists. """

    match: str    # Top list selection.
    mapping: str  # Bottom list selection.


class DisplayPage(JSONStruct):
    """ Contains graphical data for one selection in an analysis. """

    graph: HTMLGraph          # HTML graph text for this selection.
    intense_graph: HTMLGraph  # Brighter HTML text graph for this selection.
    caption: str              # Text characters drawn as a caption (possibly on a tooltip).
    board: BoardDiagram       # XML string containing this rule's SVG board diagram.
    rule_id: str              # If the selection uses a valid rule, its rule ID, else an empty string.


DisplayPageDict = Dict[str, DisplayPage]


class Display(JSONStruct):
    """ Contains a translation and graphical data for its entire analysis. """

    keys: str                      # Translation keys in RTFCRE.
    letters: str                   # Translation letters.
    pages_by_ref: DisplayPageDict  # Analysis pages keyed by HTML anchor reference.
    default_page: DisplayPage      # Default analysis page with nothing highlighted.


class Updates(JSONStruct):
    """ Contains a set of GUI updates. All fields are optional. """

    matches: Matches = None        # New items in the search lists.
    selections: Selections = None  # New selections in the search lists.
    display: Display = None        # New graphical objects.
    example_ref: str = None        # Focus reference for an example.


class JSONGUIApplication(JSONApplication):
    """ Backend for the AJAX GUI web application. Actions are independent and effectively "stateless".
        Steno rules may be parsed into a tree of nodes, each of which may have several forms of representation.
        All information for a single node is combined into a display "page" which can be used for GUI updates.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer HTTP requests and more opportunities for caching. """

    def __init__(self, engine:Engine) -> None:
        self._engine = engine

    def run(self, obj:JSONDict) -> JSONDict:
        """ Perform a requested app action. Engine state must be reset each time. """
        if not isinstance(obj, dict):
            raise TypeError('Top level of input data must be a JSON object.')
        req = Request(**obj)
        self._engine.set_options(req.options or {})
        method = getattr(self, "do_" + req.action)
        return method(*req.args)

    def _match(self, pattern:str, pages:int) -> Matches:
        results = self._engine.search(pattern, pages)
        can_expand = (results.pop(EXPAND_KEY, None) is not None)
        return Matches(pattern=pattern,
                       results=results,
                       can_expand=can_expand)

    def _select(self, keys:str, letters:str) -> Selections:
        match, mapping = self._engine.search_selection(keys, letters)
        return Selections(match=match,
                          mapping=mapping)

    def _draw_page(self) -> DisplayPage:
        """ Create a display page for the current rule reference. """
        return DisplayPage(graph=self._engine.draw_graph(),
                           intense_graph=self._engine.draw_graph(intense=True),
                           caption=self._engine.get_caption(),
                           board=self._engine.draw_board(),
                           rule_id=self._engine.get_example_id())

    def _display(self, keys:str, letters:str) -> Display:
        """ Run a query and return a full set of display data including all possible selections. """
        self._engine.run_query(keys, letters)
        default_page = self._draw_page()
        pages_by_ref = {}
        for ref in self._engine.get_refs():
            self._engine.select_ref(ref)
            pages_by_ref[ref] = self._draw_page()
        return Display(keys=keys,
                       letters=letters,
                       pages_by_ref=pages_by_ref,
                       default_page=default_page)

    def do_search(self, pattern:str, pages:int) -> Updates:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        return Updates(matches=self._match(pattern, pages))

    def do_query(self, keys:str, letters:str) -> Updates:
        """ Execute and return a full display of a lexer query. """
        return Updates(display=self._display(keys, letters))

    def do_query_match(self, match:str, mappings:Sequence[str]) -> Updates:
        """ Query and display the best translation in a match-mappings pair from search. """
        keys, letters = self._engine.best_translation(match, mappings)
        return Updates(selections=self._select(keys, letters),
                       display=self._display(keys, letters))

    def do_search_examples(self, link_ref:str) -> Updates:
        """ Search for examples of the named rule and display one at random. """
        pattern = self._engine.random_pattern(link_ref)
        if not pattern:
            return Updates()
        matches = self._match(pattern, 1)
        keys, letters = self._engine.random_translation(matches.results)
        return Updates(matches=matches,
                       selections=self._select(keys, letters),
                       display=self._display(keys, letters),
                       example_ref=self._engine.find_ref(link_ref))


def build_app(spectra:Spectra) -> JSONGUIApplication:
    engine = build_engine(spectra)
    engine.load_initial()
    return JSONGUIApplication(engine)

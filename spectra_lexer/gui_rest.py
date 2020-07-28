from typing import Dict, Sequence

from spectra_lexer.gui_engine import GUIEngine
from spectra_lexer.http.json import JSONApplication
from spectra_lexer.spc_board import BoardDiagram
from spectra_lexer.spc_graph import HTMLGraph
from spectra_lexer.spc_search import MatchDict


class RESTObject(dict):
    """ Record-type dictionary designed for serialization as a JSON object.
        Subclasses add annotations to specify required and optional fields. """

    def __init__(self, **kwargs) -> None:
        """ Check annotations for required fields and copy default values for optional ones. """
        super().__init__(kwargs)
        for k in self.__annotations__:
            if k not in self:
                try:
                    self[k] = getattr(self, k)
                except AttributeError:
                    raise TypeError(f'Missing required field "{k}"')
        self.__dict__ = self


class RESTInput(RESTObject):
    """ Contains user input data. """

    action: str    # Name of an action method to call.
    args: list     # Positional arguments for the method.
    options: dict  # GUI engine options to set before calling the method.


class RESTSelections(RESTObject):
    """ Contains a specific selection in the search lists. """

    match: str    # Top list selection.
    mapping: str  # Bottom list selection.


class RESTDisplayPage(RESTObject):
    """ Contains graphical data for one selection in an analysis. """

    graph: HTMLGraph          # HTML graph text for this selection.
    intense_graph: HTMLGraph  # Brighter HTML text graph for this selection.
    caption: str              # Text characters drawn as a caption (possibly on a tooltip).
    board: BoardDiagram       # XML string containing this rule's SVG board diagram.
    rule_id: str              # If the selection uses a valid rule, its rule ID, else an empty string.


class RESTDisplay(RESTObject):
    """ Contains a translation and graphical data for its entire analysis. """

    keys: str                                 # Translation keys in RTFCRE.
    letters: str                              # Translation letters.
    pages_by_ref: Dict[str, RESTDisplayPage]  # Analysis pages keyed by HTML anchor reference.
    default_page: RESTDisplayPage             # Default starting analysis page. May also be included in pages_by_ref.


class RESTUpdates(RESTObject):
    """ Contains a set of GUI updates. All fields are optional. """

    matches: MatchDict = None          # New items in the search lists.
    selections: RESTSelections = None  # New selections in the search lists.
    display: RESTDisplay = None        # New graphical objects.


class RESTGUIApplication(JSONApplication):
    """ Backend for the AJAX GUI web application. Actions are independent and effectively "stateless".
        Steno rules may be parsed into a tree of nodes, each of which may have several forms of representation.
        All information for a single node is combined into a display "page" which can be used for GUI updates.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer HTTP requests and more opportunities for caching. """

    def __init__(self, engine:GUIEngine) -> None:
        self._engine = engine

    def run(self, d:dict) -> dict:
        """ Perform a REST app action. Engine state must be reset each time. """
        obj = RESTInput(**d)
        self._engine.set_options(obj.options)
        method = getattr(self, "REST_" + obj.action)
        return method(*obj.args)

    def _draw_page(self, ref="") -> RESTDisplayPage:
        """ Create a display page for a rule <ref>erence, or a default page if ref is empty or invalid. """
        return RESTDisplayPage(graph=self._engine.draw_graph(ref),
                               intense_graph=self._engine.draw_graph(ref, intense=True),
                               caption=self._engine.get_caption(ref),
                               board=self._engine.draw_board(ref),
                               rule_id=self._engine.get_example_id(ref))

    def _display(self, keys:str, letters:str) -> RESTDisplay:
        """ Run a query and return a full set of display data, including all possible selections. """
        refs = self._engine.query(keys, letters)
        return RESTDisplay(keys=keys,
                           letters=letters,
                           pages_by_ref={ref: self._draw_page(ref) for ref in refs},
                           default_page=self._draw_page())

    def _select(self, keys:str, letters:str) -> RESTSelections:
        match, mapping = self._engine.search_selection(keys, letters)
        return RESTSelections(match=match,
                              mapping=mapping)

    def REST_search(self, pattern:str, pages=1) -> RESTUpdates:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        return RESTUpdates(matches=self._engine.search(pattern, pages))

    def REST_query(self, keys:str, letters:str) -> RESTUpdates:
        """ Execute and return a full display of a lexer query. """
        return RESTUpdates(display=self._display(keys, letters))

    def REST_query_match(self, match:str, mappings:Sequence[str]) -> RESTUpdates:
        """ Query and display the best translation in a match-mappings pair from search. """
        keys, letters = self._engine.best_translation(match, mappings)
        return RESTUpdates(selections=self._select(keys, letters),
                           display=self._display(keys, letters))

    def REST_search_examples(self, link_ref:str) -> RESTUpdates:
        """ Search for examples of the named rule and display one at random. """
        pattern = self._engine.random_pattern(link_ref)
        if not pattern:
            return RESTUpdates()
        matches = self._engine.search(pattern)
        keys, letters = self._engine.random_translation(matches)
        return RESTUpdates(matches=matches,
                           selections=self._select(keys, letters),
                           display=self._display(keys, letters))

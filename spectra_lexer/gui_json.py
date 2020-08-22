from typing import Dict, Sequence

from spectra_lexer.engine import Engine
from spectra_lexer.http.json import JSONApplication, JSONDict, JSONList, JSONStruct
from spectra_lexer.spc_board import BoardDiagram
from spectra_lexer.spc_graph import HTMLGraph
from spectra_lexer.spc_search import MatchDict


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
    default_page: DisplayPage      # Default starting analysis page. May also be included in pages_by_ref.


class Updates(JSONStruct):
    """ Contains a set of GUI updates. All fields are optional. """

    matches: MatchDict = None      # New items in the search lists.
    selections: Selections = None  # New selections in the search lists.
    display: Display = None        # New graphical objects.


class JSONGUIApplication(JSONApplication):
    """ Backend for the AJAX GUI web application. Actions are independent and effectively "stateless".
        Steno rules may be parsed into a tree of nodes, each of which may have several forms of representation.
        All information for a single node is combined into a display "page" which can be used for GUI updates.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer HTTP requests and more opportunities for caching. """

    def __init__(self, engine:Engine) -> None:
        self._engine = engine

    def run(self, *, action:str, args:JSONList, options:JSONDict, **_) -> JSONDict:
        """ Perform a named app action. Engine state must be reset each time.
            action -  Name of an action method to call.
            args -    Positional arguments for the method.
            options - GUI engine options to set before calling the method. """
        self._engine.set_options(options)
        method = getattr(self, "do_" + action)
        return method(*args)

    def _draw_page(self, ref="") -> DisplayPage:
        """ Create a display page for a rule <ref>erence, or a default page if <ref> is empty or invalid. """
        return DisplayPage(graph=self._engine.draw_graph(ref),
                           intense_graph=self._engine.draw_graph(ref, intense=True),
                           caption=self._engine.get_caption(ref),
                           board=self._engine.draw_board(ref),
                           rule_id=self._engine.get_example_id(ref))

    def _compile_pages(self) -> DisplayPageDict:
        """ Compile a full set of display data including all possible selections. """
        refs = self._engine.get_refs()
        return {ref: self._draw_page(ref) for ref in refs}

    def _display(self, keys:str, letters:str) -> Display:
        """ Run a query and return a full set of display data. """
        self._engine.run_query(keys, letters)
        return Display(keys=keys,
                       letters=letters,
                       pages_by_ref=self._compile_pages(),
                       default_page=self._draw_page())

    def _select(self, keys:str, letters:str) -> Selections:
        match, mapping = self._engine.search_selection(keys, letters)
        return Selections(match=match,
                          mapping=mapping)

    def do_search(self, pattern:str, pages=1) -> Updates:
        """ Do a new search and return results (unless the pattern is just whitespace). """
        return Updates(matches=self._engine.search(pattern, pages))

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
        matches = self._engine.search(pattern)
        keys, letters = self._engine.random_translation(matches)
        return Updates(matches=matches,
                       selections=self._select(keys, letters),
                       display=self._display(keys, letters))

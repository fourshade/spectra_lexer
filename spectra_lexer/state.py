""" Module for the GUI state machine. """

from typing import Any, List

from spectra_lexer.option import ConfigOption
from spectra_lexer.steno import StenoEngine


class ViewConfig:
    """ State attributes that can be user-configured (desktop), or sent in query strings (HTTP). """
    compound_board: bool = ConfigOption("board", "compound_keys", True,
                                        "Show special labels for compound keys (i.e. `f` instead of TP).")
    recursive_graph: bool = ConfigOption("graph", "recursive", True,
                                         "Include rules that make up other rules.")
    compressed_graph: bool = ConfigOption("graph", "compressed", True,
                                          "Compress the graph vertically to save space.")
    match_all_keys: bool = ConfigOption("lexer", "need_all_keys", False,
                                        "Only return lexer results that match every key in the stroke.")
    matches_per_page: int = ConfigOption("search", "match_limit", 100,
                                         "Maximum number of matches returned on one page of a search.")
    links_enabled: bool = ConfigOption("search", "example_links", True,
                                       "Show hyperlinks to indexed examples of selected rules.")


class ViewState(ViewConfig):
    """ The primary GUI state machine. Contains a complete representation of the state of the main GUI operations.
        The general flow of information goes from the search box, to a list of words matching the search, to a list
        of mappings (strokes <-> translations) that correspond to the chosen word, and finally to the lexer.
        After the lexer is finished with a translation, a graph and board diagram are generated.
        Various steps of the process may be done automatically; for example, if there is only one
        possible mapping of a certain word, it will be chosen automatically and a lexer query sent. """

    _MORE_TEXT: str = "(more...)"  # Text displayed as the final list item, allowing the user to expand the search.

    # The user may manipulate the GUI to change these values.
    input_text: str = ""               # Last pattern from user textbox input.
    match_selected: str = ""           # Last selected match from the upper list.
    mapping_selected: str = ""         # Last selected match from the lower list.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    translation: list = ["", ""]       # Currently diagrammed translation on graph.
    graph_node_ref: str = ""           # Last node identifier on the graph ("" for empty space).
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # The user typically can't change these values directly. They are held for future reference.
    link_ref: str = ""             # Name for the most recent rule (if there are examples in the index).
    page_count: int = 1            # Number of pages in the upper list.
    graph_has_focus: bool = False  # Is a node under focus on the graph?

    # Pure output values.
    matches: list = []           # New items in the upper list.
    mappings: list = []          # New items in the lower list.
    graph_text: str = ""         # HTML formatted text for the graph.
    board_caption: str = ""      # Rule caption above the board.
    board_xml_data: bytes = b""  # Raw XML data string for an SVG board.
    show_link: bool = False      # If True, there are examples in the index.

    # Web-specific - for browsers with poor monospace font support.
    graph_compat: bool = False   # If True, draw the graph using HTML tables with a cell for each character.

    def __init__(self, engine:StenoEngine) -> None:
        self._engine = engine  # Has access to outside components.
        self._modified = {}    # Tracks attributes that are changed by action methods.

    def __setattr__(self, name:str, value:Any) -> None:
        """ Add public attributes that are modified to the tracking dict. """
        super().__setattr__(name, value)
        if not name.startswith("_"):
            self._modified[name] = value

    def update(self, *args, **kwargs) -> None:
        """ Update state attributes without affecting the modified tracker. """
        self.__dict__.update(*args, **kwargs)

    def get_modified(self) -> dict:
        """ Return all state attributes that have been modified, then reset the tracker. """
        last_modified = self._modified
        self._modified = {}
        return last_modified

    def run(self, action:str) -> None:
        """ Run an action method (if valid). """
        method = getattr(self, f"RUN{action}")
        method()

    def RUNSearchExamples(self) -> None:
        """ When a link is clicked, search for examples of the named rule and select one. """
        selection, self.input_text = self._engine.find_example(self.link_ref, strokes=self.mode_strokes)
        self.page_count = 1
        self._search()
        if selection in self.matches:
            self.match_selected = selection
            self._lookup()

    def RUNSearch(self) -> None:
        """ Do a new search unless the input is blank. """
        self.page_count = 1
        if not self.input_text:
            self._set_matches([])
        else:
            self._search()
            # Automatically select the match if there was only one.
            if len(self.matches) == 1:
                self.match_selected = self.matches[0]
                self._lookup()

    def RUNLookup(self) -> None:
        """ If the user clicked "more", search again with another page. """
        if self.match_selected == self._MORE_TEXT:
            self.page_count += 1
            self._search()
        else:
            self._lookup()

    def _search(self) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        count = self.page_count * self.matches_per_page
        matches = self._call_search(count=count)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(self._MORE_TEXT)
        self._set_matches(matches)

    def _set_matches(self, matches:List[str]) -> None:
        """ Set a new match list. This invalidates the previous mappings. """
        self.matches = matches
        self.mappings = []

    def _lookup(self) -> None:
        """ Look up mappings and display them in the lower list. """
        match = self.match_selected
        mappings = self.mappings = self._call_search(match)
        if mappings:
            # A lone mapping should be highlighted automatically and displayed on its own.
            selection, *others = mappings
            if others:
                # If there is more than one mapping, make a query to select the best combination.
                selection = self._engine.lexer_best_strokes(mappings, match)
            self.mapping_selected = selection
            self._query_from_selection()

    def _call_search(self, *args, **kwargs) -> List[str]:
        kwargs.update(strokes=self.mode_strokes, regex=self.mode_regex)
        return self._engine.search(self.input_text, *args, **kwargs)

    def RUNSelect(self) -> None:
        """ Do a lexer query based on the current search selections. """
        self._query_from_selection()

    def _query_from_selection(self) -> None:
        """ The order of lexer parameters must be reversed for strokes mode. """
        self.translation = translation = [self.match_selected, self.mapping_selected]
        if not self.mode_strokes:
            translation.reverse()
        self._new_graph()

    def RUNQuery(self) -> None:
        """ Execute and display a graph of a lexer query. """
        self._new_graph()

    def _new_graph(self) -> None:
        """ A new graph should clear the last node ref and look for a new one that uses the same rule. """
        self.graph_node_ref = ""
        self._exec_query(self.graph_has_focus, True)

    def RUNGraphOver(self) -> None:
        """ On mouseover, highlight the current graph node temporarily if nothing is focused.
            Mouseovers should do nothing as long as focus is active. """
        if not self.graph_has_focus:
            self._exec_query(False, False)

    def RUNGraphClick(self) -> None:
        """ On click, find the current graph node and set focus on it (or clear focus if None). """
        self._exec_query(False, True)

    def _exec_query(self, find_rule:bool, set_focus:bool) -> None:
        """ Execute a new lexer query and load the state with the output to draw the graph and board.
            If <set_focus> is True, lock onto any valid selection with a bright color.
            If <find_rule> is True, attempt to move focus to a node with the same rule as the previous one. """
        keys, letters = self.translation
        if not (keys and letters):
            return
        select_ref = self.link_ref if find_rule else self.graph_node_ref
        data = self._engine.run(keys, letters,
                                select_ref=select_ref,
                                find_rule=find_rule,
                                set_focus=set_focus,
                                board_ratio=self.board_aspect_ratio,
                                match_all_keys=self.match_all_keys,
                                recursive_graph=self.recursive_graph,
                                compressed_graph=self.compressed_graph,
                                graph_compat=self.graph_compat,
                                compound_board=self.compound_board)
        self.graph_text, self.graph_has_focus, self.link_ref, self.board_caption, self.board_xml_data = data
        self.show_link = bool(self.link_ref) and self.links_enabled

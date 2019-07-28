from typing import List, Optional, Tuple

from spectra_lexer.resource import StenoRule
from spectra_lexer.view import VIEW

MORE_TEXT: str = "(more...)"  # Text displayed as the final list item, allowing the user to expand the search.
INDEX_DELIM: str = ";"        # Delimiter between rule name and query for index searches.


class ViewState:
    """ Contains a complete representation of the state of the GUI. """

    # The user may manipulate the GUI to change these values.
    input_text: str = ""               # Last pattern from user textbox input.
    match_selected: str = ""           # Last selected match from the upper list.
    mapping_selected: str = ""         # Last selected match from the lower list.
    mode_strokes: bool = False         # If True, search for strokes instead of translations.
    mode_regex: bool = False           # If True, perform search using regex characters.
    translation: str = ""              # String form of currently diagrammed translation on graph.
    graph_node_ref: str = ""           # Last node identifier on the graph ("" for empty space).
    board_aspect_ratio: float = 100.0  # Last aspect ratio for board viewing area.

    # The user typically can't change these values directly. They are held for future reference.
    link_ref: str = ""                 # Name for the most recent rule (if there are examples in the index).
    page_count: int = 1                # Number of pages in the upper list.
    graph_has_selection: bool = False  # Is there a selected rule on the graph?

    # Pure output values.
    matches: list = []           # New items in the upper list.
    mappings: list = []          # New items in the lower list.
    graph_text: str = ""         # HTML formatted text for the graph.
    board_caption: str = ""      # Rule caption above the board.
    board_xml_data: bytes = b""  # Raw XML data string for an SVG board.

    _DEFAULTS = {k: v for k, v in locals().items() if not k.startswith("_")}  # Keep track of defaults for the above.

    # Web-specific config options.
    graph_compat: bool = False   # Draw the graph using tables for browsers with bad monospace font support.

    _result: dict  # Holds all attributes and values that were changed since creation.
    _view: VIEW    # Has access to all outside components.

    def __init__(self, d:dict, view:VIEW):
        """ Update the attribute dict directly with a state dict <d>.
            Empty the original dict and keep it to return with the results. It may have metadata on it. """
        self.__dict__.update(d)
        d.clear()
        self._result = d
        self._view = view

    def __setattr__(self, attr:str, value) -> None:
        """ Add any modified public attributes to the results dict. """
        super().__setattr__(attr, value)
        if not attr.startswith("_"):
            self._result[attr] = value

    def __getattr__(self, attr:str):
        return getattr(self._view, attr)

    def run(self, action:str) -> Optional[dict]:
        """ Run an action (if valid) and return the result dict with all items that were changed. """
        if action.startswith("VIEW") and hasattr(self, action):
            method = getattr(self, action)
            method()
            return self._result

    def VIEWReset(self) -> None:
        """ Reset the GUI state with the default value of each public, non-callable class attribute. """
        self._result.update(self._DEFAULTS)

    def VIEWSearchExamples(self) -> None:
        """ When a link is clicked, search for examples of the named rule and select one. """
        link_ref = self.link_ref
        selection = self._index.find_example(link_ref, strokes=self.mode_strokes)
        self.input_text = INDEX_DELIM.join([link_ref, selection])
        self.page_count = 1
        self._search()
        if selection in self.matches:
            self.match_selected = selection
            self._lookup()

    def VIEWSearch(self) -> None:
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

    def VIEWLookup(self) -> None:
        """ If the user clicked "more", search again with another page. """
        if self.match_selected == MORE_TEXT:
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
            matches.append(MORE_TEXT)
        self._set_matches(matches)

    def _set_matches(self, matches:List[str]) -> None:
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
                # If there is more than one mapping, make a product query to select the best combination.
                rule = self.LXLexerQueryProduct(mappings, [match])
                selection = rule.keys
            self.mapping_selected = selection
            self._query_from_selection()

    def _call_search(self, match:str=None, **kwargs) -> List[str]:
        """ Choose an index to use based on delimiters and call a search on it. """
        *keys, pattern = self.input_text.split(INDEX_DELIM, 1)
        index = self._index if keys else self._translations
        return index.search(*keys, match or pattern, strokes=self.mode_strokes, regex=self.mode_regex, **kwargs)

    def VIEWSelect(self) -> None:
        """ Do a lexer query based on the current search selections. """
        self._query_from_selection()

    def _query_from_selection(self) -> None:
        """ The order of strokes/word in the lexer command is reversed for strokes mode. """
        translation_params = [self.match_selected, self.mapping_selected]
        if not self.mode_strokes:
            translation_params.reverse()
        keys, letters = translation_params
        self.translation = f'{keys} -> {letters}'
        self._new_graph()

    def VIEWQuery(self) -> None:
        """ Execute and display a lexer query. """
        self._new_graph()

    def _new_graph(self) -> None:
        """ Draw a new graph. Only a previous linked example rule may be selected. """
        self.graph_node_ref = ""
        select = self.graph_has_selection
        self._new_query(select, prev=self._rules.get(self.link_ref) if select else None)

    def VIEWGraphOver(self) -> None:
        """ On mouseover, highlight the node at (row, col) temporarily if nothing is selected.
            Mouseovers should do nothing as long as a selection is active. """
        if not self.graph_has_selection:
            self._new_query(False)

    def VIEWGraphClick(self) -> None:
        """ On click, find the node owning the character at (row, col) and select it with a bright color. """
        self._new_query(True)

    def _new_query(self, select:bool, **kwargs) -> None:
        params = (*map(str.strip, self.translation.split('->', 1)),)
        if len(params) == 2 and all(params):
            rule = self.LXLexerQuery(*params, match_all_keys=self.match_all_keys)
            self.graph_text, selection = self._get_graph(rule, select, **kwargs)
            if selection:
                self.graph_has_selection = select
            else:
                self.graph_has_selection = False
                selection = rule
            self.link_ref = self._get_link(selection)
            self.board_caption = selection.caption()
            self.board_xml_data = self._get_board_data(selection)

    def _get_graph(self, rule:StenoRule, select:bool, prev:StenoRule=None) -> Tuple[str, StenoRule]:
        graph = self.LXGraphGenerate(rule, recursive=self.recursive_graph,
                                     compressed=self.compressed_graph, compat=self.graph_compat)
        return graph.render(self.graph_node_ref, prev, select)

    def _get_link(self, rule:StenoRule) -> str:
        if self.links_enabled:
            name = self._rules.inverse.get(rule, "")
            if name in self._index:
                return name
        return ""

    def _get_board_data(self, rule:StenoRule) -> bytes:
        ratio = self.board_aspect_ratio
        if self.compound_board:
            return self.LXBoardFromRule(rule, ratio)
        else:
            return self.LXBoardFromKeys(rule.keys, ratio)

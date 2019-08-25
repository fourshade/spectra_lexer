from typing import Any, List

from spectra_lexer.steno import StenoEngine, StenoRule

# State attributes that can be user-configured in the GUI version, or sent in query strings in the HTML version.
CONFIG_INFO = [("compound_board", True, "board", "compound_keys",
                "Show special labels for compound keys (i.e. `f` instead of TP)."),
               ("recursive_graph", True, "graph", "recursive",
                "Include rules that make up other rules."),
               ("compressed_graph", True, "graph", "compressed",
                "Compress the graph vertically to save space."),
               ("match_all_keys", False, "lexer", "need_all_keys",
                "Only return lexer results that match every key in the stroke."),
               ("matches_per_page", 100, "search", "match_limit",
                "Maximum number of matches returned on one page of a search."),
               ("links_enabled", True, "search", "example_links",
                "Show hyperlinks to indexed examples of selected rules.")]
# Web-specific config options, sent in query strings.
WEB_CONFIG_INFO = [("graph_compat", False, "graph", "compatibility_mode",
                    "Draw the graph using tables (for browsers with poor monospace font support.)")]


class ViewState:
    """ Contains a complete representation of the state of the main GUI. """

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
    link_ref: str = ""                 # Name for the most recent rule (if there are examples in the index).
    page_count: int = 1                # Number of pages in the upper list.
    graph_has_selection: bool = False  # Is there a selected rule on the graph?

    # Pure output values.
    matches: list = []           # New items in the upper list.
    mappings: list = []          # New items in the lower list.
    graph_text: str = ""         # HTML formatted text for the graph.
    board_caption: str = ""      # Rule caption above the board.
    board_xml_data: bytes = b""  # Raw XML data string for an SVG board.

    _result: dict         # Holds all attributes and values that were changed since creation.
    _engine: StenoEngine  # Has access to all outside components.

    def __init__(self, d:dict, engine:StenoEngine) -> None:
        """ Update the attribute dict directly with a state dict <d>. """
        self.__dict__.update(d)
        self._result = {}
        self._engine = engine

    def __setattr__(self, attr:str, value:Any) -> None:
        """ Add any modified public attributes to the results dict. """
        super().__setattr__(attr, value)
        if not attr.startswith("_"):
            self._result[attr] = value

    def run(self, action:str) -> dict:
        """ Run an action (if valid) and return the result dict with all items that were changed. """
        method = getattr(self, f"RUN{action}")
        method()
        return self._result

    def RUNSearchExamples(self) -> None:
        """ When a link is clicked, search for examples of the named rule and select one. """
        selection, self.input_text = self._engine.search_examples(self.link_ref, strokes=self.mode_strokes)
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
                pairs = [(m, match) for m in mappings]
                selection = self._engine.lexer_best_strokes(pairs)
            self.mapping_selected = selection
            self._query_from_selection()

    def _call_search(self, *args, **kwargs) -> List[str]:
        kwargs.update(strokes=self.mode_strokes, regex=self.mode_regex)
        return self._engine.search_query(self.input_text, *args, **kwargs)

    def RUNSelect(self) -> None:
        """ Do a lexer query based on the current search selections. """
        self._query_from_selection()

    def _query_from_selection(self) -> None:
        """ The order of strokes/word in the lexer command is reversed for strokes mode. """
        self.translation = translation = [self.match_selected, self.mapping_selected]
        if not self.mode_strokes:
            translation.reverse()
        self._new_graph()

    def RUNQuery(self) -> None:
        """ Execute and display a lexer query. """
        self._new_graph()

    def _new_graph(self) -> None:
        self.graph_node_ref = ""
        self._new_query(False)

    def RUNGraphOver(self) -> None:
        """ On mouseover, highlight the node at (row, col) temporarily if nothing is selected.
            Mouseovers should do nothing as long as a selection is active. """
        if not self.graph_has_selection:
            self._new_query(False)

    def RUNGraphClick(self) -> None:
        """ On click, find the node owning the character at (row, col) and select it with a bright color. """
        self._new_query(True)

    def _new_query(self, *args) -> None:
        keys, letters = self.translation
        if keys and letters:
            rule = self._engine.lexer_query(keys, letters, match_all_keys=self.match_all_keys)
            self._draw_all(rule, *args)

    def _draw_all(self, rule:StenoRule, select:bool) -> None:
        """ Draw the graph and board. Only a previous linked example rule may be selected, and only on a new graph. """
        graph = self._engine.graph_generate(rule, recursive=self.recursive_graph,
                                            compressed=self.compressed_graph, compat=self.graph_compat)
        try_prev = self.graph_has_selection and not select
        prev = self._engine.search_rules(self.link_ref) if try_prev else None
        select = select or try_prev
        self.graph_text, selection = graph.render(self.graph_node_ref, prev, select)
        if selection:
            self.graph_has_selection = select
        else:
            self.graph_has_selection = False
            selection = rule
        self._set_board_data(selection)

    def _set_board_data(self, rule:StenoRule) -> None:
        self.link_ref = self._engine.search_links(rule) if self.links_enabled else ""
        self.board_caption = rule.caption()
        ratio = self.board_aspect_ratio
        if self.compound_board:
            xml_data = self._engine.board_from_rule(rule, ratio)
        else:
            xml_data = self._engine.board_from_keys(rule.keys, ratio)
        self.board_xml_data = xml_data


# Update the class with all possible config defaults.
for key, default, *_ in (*CONFIG_INFO, *WEB_CONFIG_INFO):
    setattr(ViewState, key, default)

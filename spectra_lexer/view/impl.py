from functools import partial

from .base import ConfigOption, VIEW
from spectra_lexer.resource import StenoRule

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class ViewLayer(VIEW):
    """ Implementation for handling text graphs and selections.
        Interface to draw steno board diagram elements and the description for rules. """

    BoardConfigOption = partial(ConfigOption, "board")
    GraphConfigOption = partial(ConfigOption, "graph")
    SearchConfigOption = partial(ConfigOption, "search")

    show_compound: bool = BoardConfigOption("compound_keys", default=True,
                                            desc="Show special labels for compound keys (i.e. `f` instead of TP).")
    recursive_graph: bool = GraphConfigOption("recursive", default=True,
                                              desc="Include rules that make up other rules.")
    compressed_graph: bool = GraphConfigOption("compressed", default=True,
                                               desc="Compress the graph vertically to save space.")
    match_limit: int = SearchConfigOption("match_limit", default=100,
                                          desc="Maximum number of matches returned by a search.")
    show_links: bool = SearchConfigOption("example_links", default=True,
                                          desc="Show hyperlinks to other examples of a selected rule from an index.")
    need_all_keys: bool = SearchConfigOption("need_all_keys", default=False,
                                             desc="Only return lexer results that match every key in the stroke.")

    _last_rule: StenoRule = None        # Most recent rule from lexer.
    _last_selection: StenoRule = None   # Most recent selected rule on graph.
    _last_board_rule: StenoRule = None  # Most recent rule shown on board.
    _last_board_ratio: float = 100.0    # Last known aspect ratio for board viewing area.
    _search_pages: int = 1              # Number of pages (size <match_limit>) of search results on screen.

    def _show_rule(self, rule:StenoRule) -> None:
        """ Generate a new graph from a lexer rule and set the title. """
        self.VIEWNewTitle(str(rule))
        self._last_rule = rule
        self._last_selection = self._set_graph(rule, is_new=True, sel=self._last_selection, intense=True)

    def graph_action(self, row:int, col:int, clicked:bool) -> None:
        """ On click, find the node owning the character at (row, col) and select it with a bright color.
            On mouseover, highlight it temporarily if nothing is selected. """
        rule = self._last_rule
        if rule is not None:
            if clicked:
                self._last_selection = self._set_graph(rule, location=(row, col), intense=True)
            elif self._last_selection is None:
                self._set_graph(rule, location=(row, col))

    def _set_graph(self, rule:StenoRule, *, is_new:bool=False, location=None, sel=None, **kwargs) -> StenoRule:
        """ Select a rule and format the graph with its reference highlighted. """
        graph = self.LXGraphGenerate(rule, recursive=self.recursive_graph, compressed=self.compressed_graph)
        node = None
        if location:
            node = graph.from_character(*location)
        if sel:
            node = graph.from_rule(sel)
        active = graph.get_rule(node)
        text = graph.to_html(*filter(None, [node]), **kwargs)
        selected = active or rule
        self._make_board(selected)
        self._search_set_example_rule(selected)
        # A new graph should scroll to the top by default. Otherwise don't allow the graph to scroll.
        self.VIEWNewGraph(text, scroll_to="top" if is_new else None)
        return active

    def board_resize(self, width:int, height:int) -> None:
        self._last_board_ratio = width / height
        if self._last_board_rule is not None:
            self._make_board(self._last_board_rule)

    def _make_board(self, rule:StenoRule) -> None:
        xml_data = self.LXBoardFromRule(rule, self._last_board_ratio, show_compound=self.show_compound)
        if xml_data:
            self._last_board_rule = rule
            self.VIEWNewBoard(xml_data)

    def _search_set_example_rule(self, rule:StenoRule) -> None:
        link_ref = self.LXSearchFindLink(rule) if self.show_links else ""
        self.VIEWNewCaption(rule.caption())
        self.VIEWSetLink(link_ref)

    def search_find_examples(self, *, pattern:str=..., match:str=..., **state) -> None:
        """ If the search engine found examples, show them in the matches list and select one. """
        search_text, selection = self.LXSearchExamples(**state)
        self.VIEWSetInput(search_text)
        self.search_edit_input(search_text, selection=selection, **state)

    def search_edit_input(self, pattern:str, **state) -> None:
        self._search_pages = 1
        if pattern:
            self.search(pattern, **state)

    def search(self, pattern:str, *, match:str=..., selection:str=None, **state) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        count = self._search_pages * self.match_limit
        matches = self.LXSearchQuery(pattern, count=count, **state)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(_MORE_TEXT)
        # Automatically select the match if there was only one.
        if selection is None and len(matches) == 1:
            selection = matches[0]
        # Show the new match list and wipe the mappings list if no lookup is performed.
        self.VIEWSetMatches(matches, selection)
        if selection is not None:
            self.lookup(pattern, selection, **state)
        else:
            self.VIEWSetMappings([])

    def search_choose_match(self, pattern:str, match:str, **state) -> None:
        if match == _MORE_TEXT:
            # If the user clicked "more", increment the page count and search again. Do not find mappings.
            self._search_pages += 1
            self.search(pattern, **state)
        else:
            self.lookup(pattern, match, **state)

    def lookup(self, pattern:str, match:str, *, mapping:str=..., **state) -> None:
        """ Look up mappings and display them in the lower list. """
        mappings = self.LXSearchLookup(pattern, match, **state)
        # A lone mapping should be highlighted automatically and displayed on its own.
        selection = mappings[0] if len(mappings) == 1 else None
        if selection is not None:
            self.search_choose_mapping(match, selection, **state)
        elif mappings:
            # If there is more than one mapping, make a product query to select the best combination.
            result = self._show_query(self.LXLexerQueryProduct, mappings, [match])
            if result.keys in mappings:
                selection = result.keys
        self.VIEWSetMappings(mappings, selection)

    def search_choose_mapping(self, match:str, mapping:str, strokes:bool=False, **state) -> None:
        """ The order of strokes/word in the lexer command is reversed for strokes mode. """
        args = [match, mapping] if strokes else [mapping, match]
        self._show_query(self.LXLexerQuery, *args)

    def _show_query(self, cmd, *args) -> StenoRule:
        """ We must send a lexer query to show a translation. """
        result = cmd(*args, need_all_keys=self.need_all_keys)
        self._show_rule(result)
        return result

    def VIEWQuery(self, strokes:str, word:str, **kwargs) -> None:
        self._show_rule(self.LXLexerQuery(strokes, word, **kwargs))

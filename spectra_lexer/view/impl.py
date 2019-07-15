from typing import List, Tuple

from .base import ConfigOption, VIEW
from .state import ViewState
from spectra_lexer.resource import StenoRule


class InnerViewLayer(VIEW):
    """ Inner layer to encapsulate all config values and engine calls. """

    _MORE_TEXT: str = "(more...)"  # Text displayed as the final list item, allowing the user to expand the search.
    _INDEX_DELIM: str = ";"        # Delimiter between rule name and query for index searches.

    show_compound: bool = ConfigOption("board", "compound_keys", default=True,
                                       desc="Show special labels for compound keys (i.e. `f` instead of TP).")
    recursive_graph: bool = ConfigOption("graph", "recursive", default=True,
                                         desc="Include rules that make up other rules.")
    compressed_graph: bool = ConfigOption("graph", "compressed", default=True,
                                          desc="Compress the graph vertically to save space.")
    match_limit: int = ConfigOption("search", "match_limit", default=100,
                                    desc="Maximum number of matches returned on one page of a search.")
    show_links: bool = ConfigOption("search", "example_links", default=True,
                                    desc="Show hyperlinks to other examples of a selected rule from an index.")
    need_all_keys: bool = ConfigOption("search", "need_all_keys", default=False,
                                       desc="Only return lexer results that match every key in the stroke.")

    def _call_examples(self, link_ref:str, strokes:bool) -> Tuple[str, str]:
        match = self.LXSearchExamples(link_ref, strokes=strokes)
        pattern = self._INDEX_DELIM.join([link_ref, match])
        return pattern, match

    def _call_search(self, pattern:str, existing_count:int=0, strokes:bool=False, regex:bool=False) -> List[str]:
        """ However many items are currently saved on the list (usually none), add one full page to that number. """
        if not pattern:
            return []
        count = existing_count + self.match_limit
        pattern, kwargs = self._parse_pattern(pattern)
        matches = self.LXSearchQuery(pattern, count=count, strokes=strokes, regex=regex, **kwargs)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(self._MORE_TEXT)
        return matches

    def _wants_more(self, match:str) -> bool:
        return (match == self._MORE_TEXT)

    def _call_lookup(self, pattern:str, match:str, strokes:bool) -> List[str]:
        _, kwargs = self._parse_pattern(pattern)
        return self.LXSearchQuery(match, count=None, strokes=strokes, **kwargs)

    def _call_query(self, keys:str, letters:str) -> StenoRule:
        return self.LXLexerQuery(keys, letters, need_all_keys=self.need_all_keys)

    def _call_multi_query(self, keys:List[str], letters:List[str]) -> StenoRule:
        return self.LXLexerQueryProduct(keys, letters, need_all_keys=self.need_all_keys)

    def _call_graph(self, rule:StenoRule, **kwargs) -> Tuple[str, StenoRule]:
        return self.LXGraphGenerate(rule, recursive=self.recursive_graph, compressed=self.compressed_graph, **kwargs)

    def _call_find_link(self, rule:StenoRule) -> str:
        return self.LXSearchFindLink(rule) if self.show_links else ""

    def _call_board(self, rule:StenoRule, ratio:float) -> bytes:
        return self.LXBoardFromRule(rule, ratio) if self.show_compound else self.LXBoardFromKeys(rule.keys, ratio)

    def _parse_pattern(self, pattern:str) -> Tuple[str, dict]:
        *before, pattern = pattern.split(self._INDEX_DELIM, 1)
        kwargs = {"index_key": before[0]} if before else {}
        return pattern, kwargs


class ViewLayer(InnerViewLayer):
    """ Implementation layer for handling searches, text graphs, selections, and steno board diagrams. """

    def VIEWSearchExamples(self, state:ViewState) -> None:
        state.input_text, selection = self._call_examples(state.link_ref, state.mode_strokes)
        self._search(state)
        if selection in state.matches:
            state.match_selected = selection
            self._lookup(state)

    def VIEWSearch(self, state:ViewState) -> None:
        self._search(state)
        # Automatically select the match if there was only one.
        if state.match_count == 1:
            state.match_selected = state.matches[0]
            self._lookup(state)

    def VIEWLookup(self, state:ViewState) -> None:
        """ If the user clicked "more", search again with another page. """
        if self._wants_more(state.match_selected):
            self._search(state, state.match_count)
        else:
            self._lookup(state)

    def _search(self, state:ViewState, existing_count:int=0) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        pattern = state.input_text
        matches = state.matches = self._call_search(pattern, existing_count, state.mode_strokes, state.mode_regex)
        state.match_count = len(matches)
        state.mappings = []

    def _lookup(self, state:ViewState) -> None:
        """ Look up mappings and display them in the lower list. """
        pattern = state.input_text
        match = state.match_selected
        strokes = state.mode_strokes
        mappings = state.mappings = self._call_lookup(pattern, match, strokes)
        if len(mappings) == 1:
            # A lone mapping should be highlighted automatically and displayed on its own.
            state.mapping_selected = mappings[0]
            self._query_from_selection(state)
        elif mappings:
            # If there is more than one mapping, make a product query to select the best combination.
            rule = self._call_multi_query(mappings, [match])
            state.mapping_selected = rule.keys
            self._query_from_selection(state)

    def VIEWSelect(self, state:ViewState) -> None:
        self._query_from_selection(state)

    def _query_from_selection(self, state:ViewState) -> None:
        """ The order of strokes/word in the lexer command is reversed for strokes mode. """
        translation_params = [state.match_selected, state.mapping_selected]
        if not state.mode_strokes:
            translation_params.reverse()
        state.set_query_params(*translation_params)
        self._new_graph(state)

    def VIEWQuery(self, state:ViewState) -> None:
        self._new_graph(state)

    def _new_graph(self, state:ViewState) -> None:
        """ Draw a new graph. Only a previous linked example rule may be selected. """
        state.graph_node_ref = ""
        select = state.graph_has_selection
        self._new_query(state, select, prev=self.RULES.get(state.link_ref) if select else None)

    def VIEWGraphOver(self, state:ViewState) -> None:
        """ Handle a mouseover action. Mouseovers should do nothing as long as a selection is active. """
        if not state.graph_has_selection:
            self._new_query(state, False)

    def VIEWGraphClick(self, state:ViewState) -> None:
        """ Handle a click action. """
        self._new_query(state, True)

    def _new_query(self, state:ViewState, select:bool, **kwargs) -> None:
        params = state.get_query_params()
        if params is not None:
            rule = self._call_query(*params)
            state.graph_text, selection = self._call_graph(rule, select=select, ref=state.graph_node_ref, **kwargs)
            state.graph_has_selection = bool(selection and select)
            self._set_board(state, selection or rule)

    def _set_board(self, state:ViewState, rule:StenoRule) -> None:
        state.link_ref = self._call_find_link(rule)
        state.board_caption = rule.caption()
        state.board_xml_data = self._call_board(rule, state.board_aspect_ratio)

    def VIEWAction(self, action:str, state:ViewState, **cfg_override) -> None:
        """ Interface for exchanging state variables with the GUI. """
        if hasattr(self, action) and action.startswith("VIEW"):
            getattr(self, action)(state)
        self.VIEWActionResult(state)

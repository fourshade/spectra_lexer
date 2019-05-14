from typing import List, Tuple

from .base import ConfigOption, VIEW
from .state import ViewState
from spectra_lexer.resource import StenoRule
from spectra_lexer.steno import StenoGraph


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
                                    desc="Maximum number of matches returned by a search.")
    show_links: bool = ConfigOption("search", "example_links", default=True,
                                    desc="Show hyperlinks to other examples of a selected rule from an index.")
    need_all_keys: bool = ConfigOption("search", "need_all_keys", default=False,
                                       desc="Only return lexer results that match every key in the stroke.")

    def _call_examples(self, link_ref:str, strokes:bool) -> Tuple[str, str]:
        match = self.LXSearchExamples(link_ref)[not strokes]
        pattern = self._INDEX_DELIM.join([link_ref, match])
        return pattern, match

    def _call_search(self, pattern:str, existing_count:int=0, strokes:bool=False, regex:bool=False) -> List[str]:
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
        return self.LXSearchLookup(match, strokes=strokes, **kwargs)

    def _order_selection(self, match:str, mapping:str, strokes:bool) -> List[str]:
        return [match, mapping] if strokes else [mapping, match]

    def _call_query(self, keys, letters) -> StenoRule:
        if isinstance(keys, str):
            cmd = self.LXLexerQuery
        else:
            cmd = self.LXLexerQueryProduct
        return cmd(keys, letters, need_all_keys=self.need_all_keys)

    def _call_graph(self, main_rule:StenoRule) -> StenoGraph:
        return self.LXGraphGenerate(main_rule, recursive=self.recursive_graph, compressed=self.compressed_graph)

    def _call_find_link(self, rule:StenoRule) -> str:
        return self.LXSearchFindLink(rule) if self.show_links else ""

    def _call_board(self, rule:StenoRule, ratio:float) -> bytes:
        return self.LXBoardFromRule(rule, ratio) if self.show_compound else self.LXBoardFromKeys(rule.keys, ratio)

    def _parse_pattern(self, pattern:str) -> Tuple[str, dict]:
        *before, pattern = pattern.split(self._INDEX_DELIM, 1)
        kwargs = {"index_key": before[0]} if before else {}
        return pattern, kwargs


class ViewLayer(InnerViewLayer):
    """ Implementation layer for handling text graphs, selections, and steno board diagrams. """

    def _search_examples(self, state:ViewState) -> None:
        ref = state.link_ref
        strokes = state.mode_strokes
        text, selection = self._call_examples(ref, strokes)
        state.input_text = text
        state.matches = self._call_search(text, 0, strokes)
        state.match_selected = selection

    def _search(self, state:ViewState, existing_count:int=0) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        matches = self._call_search(state.input_text, existing_count, state.mode_strokes, state.mode_regex)
        # Automatically select the match if there was only one.
        state.matches = matches
        state.mappings = []
        if len(matches) == 1:
            state.match_selected = matches[0]
            self._lookup(state)

    def _user_lookup(self, state:ViewState) -> None:
        """ If the user clicked "more", search again with another page. """
        if self._wants_more(state.match_selected):
            self._search(state, len(state.matches))
        else:
            self._lookup(state)

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
            result = self._call_query(mappings, [match])
            keys = state.mapping_selected = result.keys
            state.graph_translation = [keys, match]
            self._new_query(state)

    def _query_from_selection(self, state:ViewState) -> None:
        """ Generate a new graph from a lexer rule and set the title.
            The order of strokes/word in the lexer command is reversed for strokes mode. """
        state.graph_translation = self._order_selection(state.match_selected, state.mapping_selected, state.mode_strokes)
        self._new_query(state)

    def _new_query(self, state:ViewState) -> None:
        state.graph_location = None
        self._graph_action(state, intense=True)

    def _graph_action(self, state, intense:bool=False) -> None:
        translation = state.graph_translation
        if translation is not None:
            rule = self._call_query(*translation)
            self._set_graph(state, rule, intense)

    def _set_graph(self, state:ViewState, main_rule:StenoRule, intense:bool) -> None:
        """ Select a rule and format the graph with its reference highlighted. """
        ref = state.link_ref
        has_selection = state.graph_has_selection
        location = state.graph_location
        ratio = state.board_aspect_ratio
        graph = self._call_graph(main_rule)
        node = None
        if location is not None and (not has_selection or intense):
            node = graph.from_character(*location)
        elif has_selection:
            node = graph.from_rule(self.RULES.get(ref))
        highlighted = graph.get_rule(node)
        board_rule = highlighted or main_rule
        if highlighted:
            state.link_ref = self._call_find_link(highlighted)
        if intense:
            state.graph_has_selection = bool(highlighted)
        state.graph_title = str(main_rule)
        state.graph_text = graph.to_html(*filter(None, [node]), intense=intense)
        state.board_caption = board_rule.caption()
        state.board_xml_data = self._call_board(board_rule, ratio)


class OuterViewLayer(ViewLayer):
    """ Interface layer for exchanging state variables with the GUI. """

    def VIEWSearchExamples(self, state:ViewState) -> None:
        self._search_examples(state)
        self._lookup(state)

    def VIEWSearch(self, state:ViewState) -> None:
        if state.input_text:
            self._search(state)

    def VIEWLookup(self, state:ViewState) -> None:
        self._user_lookup(state)

    def VIEWQuery(self, state:ViewState) -> None:
        self._query_from_selection(state)

    def VIEWGraphOver(self, state:ViewState) -> None:
        if not state.graph_has_selection:
            self._graph_action(state)

    def VIEWGraphClick(self, state:ViewState) -> None:
        self._graph_action(state, intense=True)

    def VIEWAction(self, state:ViewState, action:str) -> ViewState:
        if hasattr(self, action) and action.startswith("VIEW"):
            getattr(self, action)(state)
        return state

from typing import List

from .graph import VIEWGraph
from spectra_lexer.core import Component, Command, Signal
from spectra_lexer.steno import LXLexer, LXSearch
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.system import ConfigOption
from spectra_lexer.utils import ensure_iterable


# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class VIEWSearch:
    """ Provides GUI support services for search. """

    @Command
    def edit_input(self, pattern:str, **state) -> None:
        """ The string in the search input box has changed. Do a new search unless the input is blank. """
        raise NotImplementedError

    @Command
    def choose_match(self, pattern:str, match:str, **state) -> None:
        """ The user has chosen an item in the upper matches list. Do a lookup after special checks. """
        raise NotImplementedError

    @Command
    def choose_mapping(self, match:str, mapping:str, **state) -> None:
        """ The user has chosen an item in the lower mappings list. Send a display command. """
        raise NotImplementedError

    @Command
    def find_examples(self, rule_name:str, **state) -> None:
        """ When a link is clicked, search for examples of the named rule. """
        raise NotImplementedError

    class Input:
        @Signal
        def on_view_search_input(self, text:str) -> None:
            raise NotImplementedError

    class Matches:
        @Signal
        def on_view_search_matches(self, str_list:List[str]) -> None:
            raise NotImplementedError

    class MatchFocus:
        @Signal
        def on_view_search_match_focus(self, key:str) -> None:
            raise NotImplementedError

    class Mappings:
        @Signal
        def on_view_search_mappings(self, str_list:List[str]) -> None:
            raise NotImplementedError

    class MappingFocus:
        @Signal
        def on_view_search_mapping_focus(self, key:str) -> None:
            raise NotImplementedError

    class NewInfo:
        @Signal
        def on_view_info(self, caption:str, link_ref:str) -> None:
            raise NotImplementedError


class SearchView(Component, VIEWSearch,
                 VIEWGraph.RuleSelected):

    match_limit: int = ConfigOption("search", "match_limit", default=100,
                                    desc="Maximum number of matches returned by a search.")
    show_links: bool = ConfigOption("search", "example_links", default=True,
                                    desc="Show hyperlinks to other examples of a selected rule. Requires an index.")
    need_all_keys: bool = ConfigOption("lexer", "need_all_keys", default=False,
                                       desc="Only return lexer results that match every key in the stroke.")

    _pages: int = 1  # Number of pages (size <match_limit>) of search results on screen.

    def _reset_pages(self) -> None:
        self._pages = 1

    def _get_count(self):
        return self._pages * self.match_limit

    def edit_input(self, pattern:str, **state) -> None:
        self._reset_pages()
        if pattern:
            self.search(pattern, **state)

    def search(self, pattern:str, *, match:str=..., **state) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        matches = self.engine_call(LXSearch.search, pattern, count=self._get_count(), **state)
        self._show_matches(matches)
        if len(matches) == 1:
            # Automatically select the match if there was only one.
            match = matches[0]
            self._select_match(match)
            self.lookup(pattern, match, **state)

    def _show_matches(self, matches:list) -> None:
        """ If we met the count, add a final item to allow search expansion. """
        if len(matches) == self._get_count():
            matches.append(_MORE_TEXT)
        # Show the new match list and wipe the mappings list.
        self.engine_call(self.Matches, matches)
        self.engine_call(self.Mappings, [])

    def _select_match(self, match:str) -> None:
        """ Highlight a match with a command. """
        self.engine_call(self.MatchFocus, match)

    def choose_match(self, pattern:str, match:str, **state) -> None:
        if match == _MORE_TEXT:
            # If the user clicked "more", increment the page count and search again. Do not find mappings.
            self._pages += 1
            self.search(pattern, **state)
        else:
            self.lookup(pattern, match, **state)

    def lookup(self, pattern:str, match:str, *, mapping:str=..., **state) -> None:
        """ Look up mappings and display them in the lower list.
            Keep track of the last selected match so we can put together a display command with it. """
        mappings = self.engine_call(LXSearch.lookup, pattern, match, count=self._get_count(), **state)
        # Mappings may be rules. To be safe, show the string form of everything.
        self.engine_call(self.Mappings, list(map(str, mappings)))
        if len(mappings) == 1:
            # A lone mapping should be highlighted automatically and displayed on its own.
            mapping = mappings[0]
            self.engine_call(self.MappingFocus, mapping)
            self.display(match, mapping, **state)
        elif len(mappings) > 1:
            # If there is more than one mapping, we look at all possibilities.
            self.display(match, mappings, **state)

    def choose_mapping(self, **state) -> None:
        self.display(**state)

    def display(self, match:str, mapping:object, *, strokes:bool, **state) -> None:
        """ Send an engine command to display the given match and mappings object, whatever they are. """
        if not isinstance(mapping, (str, list)):
            # If the mapping is a rule, show it as if it were fresh output from the lexer.
            self.engine_call(VIEWGraph.show_generated_rule, mapping)
        else:
            # The order of strokes/word in the lexer command is reversed for a reverse dict.
            args = [match, mapping]
            if not strokes:
                args.reverse()
            # We must send a lexer query to show a translation. """
            if all(isinstance(i, str) for i in args):
                cmd = LXLexer.query
            else:
                # If there is more than one of either input, make a product query to select the best combination.
                cmd = LXLexer.query_product
                args = map(ensure_iterable, args)
            result = self.engine_call(cmd, *args, need_all_keys=self.need_all_keys)
            # Choose a relevant stroke (if any) from the result if our last search had several choices.
            if isinstance(mapping, list) and result.keys in mapping:
                self.engine_call(self.MappingFocus, result.keys)

    def find_examples(self, *, pattern:str=..., match:str=..., **state) -> None:
        """ If the search engine found examples, show them in the matches list and select one. """
        search_text, matches, selection = self.engine_call(LXSearch.find_examples, count=self._get_count(), **state)
        if matches:
            self._reset_pages()
            self.engine_call(self.Input, search_text)
            self._show_matches(matches)
            self._select_match(selection)
            self.lookup(search_text, selection, **state)

    def on_graph_rule_selected(self, rule:StenoRule) -> None:
        link_ref = self.engine_call(LXSearch.find_link, rule) if self.show_links else ""
        self.engine_call(self.NewInfo, rule.caption(), link_ref)

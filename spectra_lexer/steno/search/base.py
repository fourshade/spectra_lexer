from functools import partialmethod
from typing import Sequence

from .collection import MasterSearchDictionary
from .nexus import IndexNexus, RulesNexus, TranslationNexus
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class SearchEngine(Component):
    """ Provides steno translation search engine services to the GUI and lexer. """

    match_limit = Option("config", "search:match_limit", 100, "Maximum number of matches returned by a search.")

    _dict: MasterSearchDictionary  # Search dicts between strokes <-> translations.
    _pages: int = 1                # Number of pages of search results (each has <match_limit> results).
    _last_pattern: str = ""        # Last pattern from user textbox input.
    _last_match: str = ""          # Last search match selected by the user in the list.
    _last_mapping: object = ""     # Last used mapping object.

    def __init__(self):
        super().__init__()
        self._dict = MasterSearchDictionary()

    def new_resource(self, ntype:type, d:dict) -> None:
        self._dict.new_resource(ntype, d)

    set_index = on("new_index")(partialmethod(new_resource, IndexNexus))
    set_rules = on("new_rules")(partialmethod(new_resource, RulesNexus))
    set_translations = on("new_translations")(partialmethod(new_resource, TranslationNexus))

    @pipe("start", "new_search_state")
    def start(self) -> bool:
        """ Turn on the GUI panel once everything is set up here. """
        return True

    @on("search_mode_strokes")
    def set_mode_strokes(self, enabled:bool) -> None:
        """ Set strokes search mode on or off and retry the search. """
        self._dict.set_mode_strokes(enabled)
        self._search()

    @on("search_mode_regex")
    def set_mode_regex(self, enabled:bool) -> None:
        """ Set regex search mode on or off and retry the search. """
        self._dict.set_mode_regex(enabled)
        self._search()

    @on("search_input")
    def on_input(self, pattern:str) -> None:
        """ With new input, reset the page count and do a new search unless the input is blank. """
        # If the pattern is blank, a search would return the entire dictionary, so don't bother.
        self._pages = 1
        if pattern:
            self._last_pattern = pattern
            self._search(pattern)

    @on("search_choose_match")
    def on_choose_match(self, match:str) -> None:
        """ When a match is chosen from the upper list, do a lookup after special checks. """
        if match == _MORE_TEXT:
            # If the user clicked "more", increment the page count and search again. Do not find mappings.
            self._pages += 1
            self._search()
        else:
            self._lookup(match)

    def _search(self, pattern:str=None) -> None:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        # The match_limit is determined by the config setting and the number of "more" selections.
        count = self._pages * self.match_limit
        # If <pattern> is None, look up the previous pattern again instead.
        matches = self._dict.search(pattern or self._last_pattern, count)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(_MORE_TEXT)
        # Send the new match list and wipe the mappings list.
        self.engine_call("new_search_match_list", matches)
        self.engine_call("new_search_mapping_list", [])
        # Select a match if there was only one.
        if len(matches) == 1:
            selection = matches[0]
            self.engine_call("new_search_match_selection", selection)
            self._lookup(selection)

    def _lookup(self, match:str):
        """ Look up mappings and display them in the lower list. """
        self._last_match = match
        mappings = self._last_mapping = self._dict.lookup(match)
        # Mappings may be rules. To be safe, show the string form of everything.
        self.engine_call("new_search_mapping_list", list(map(str, mappings)))
        if len(mappings) == 1:
            # A lone mapping should be selected manually and sent on its own.
            selection = mappings[0]
            self.engine_call("new_search_mapping_selection", selection)
            self.on_choose_mapping(selection)
        elif len(mappings) > 1:
            # We don't know which mapping will be chosen in the end, so we must save all possibilities.
            self.on_choose_mapping(mappings)

    @on("search_choose_mapping")
    def on_choose_mapping(self, mapping:object) -> None:
        """ Send an engine command on the last selected match and this mapping (or a list). """
        self._last_mapping = mapping
        cmd_args = self._dict.command_args(self._last_match, mapping)
        if cmd_args is not None:
            self.engine_call(*cmd_args)

    @on("new_output")
    def on_output(self, rule:StenoRule) -> None:
        # Look for a relevant match to a rule property in the mapping list if our last search had several choices.
        if isinstance(self._last_mapping, list):
            common_items = {rule.keys.rtfcre, rule.letters, rule}.intersection(self._last_mapping)
            if common_items:
                self.engine_call("new_search_mapping_selection", str(common_items.pop()))

from typing import List, Optional

from spectra_lexer import Component
from spectra_lexer.interactive.search.collection import StringSearchDictCollection

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"
# Command prefix to indicate a rules example search.
_RULES_PREFIX = "/"


class SearchEngine(Component):
    """ Provides steno translation search engine services to the GUI and lexer. """

    match_limit = Option("config", "search:match_limit", 100, "Maximum number of matches returned by a search.")

    _dicts: StringSearchDictCollection  # Search dicts between strokes <-> translations.
    _mode_strokes: bool                 # If True, search for strokes instead of translations.
    _mode_regex: bool                   # If True, perform search using regex characters.
    _pages: int                         # Number of pages of search results (each has <match_limit> results).
    _last_input: str                    # Last known state of user textbox input.
    _last_match: str                    # Last search match selected by the user in the list.

    def __init__(self):
        """ For translation-based searches (default), spaces and hyphens should be stripped off each end. """
        super().__init__()
        self._dicts = StringSearchDictCollection(strip_chars=' -')
        self._reset()

    def _reset(self):
        """ Reset all current state. """
        self._mode_strokes = self._mode_regex = False
        self._pages = 1
        self._last_input = self._last_match = ""
        self._parse_last_input()

    @on("new_rules")
    def set_rules(self, d:dict) -> None:
        """ Use the rules dictionary to search examples. Prefix and suffix reference symbols should be stripped. """
        self._dicts.new("rules", d, strip_chars=' .+-~')

    @pipe("new_translations", "new_search_state")
    def set_translations(self, d:dict) -> bool:
        """ Create master dictionaries to search in either direction from the raw translations dict given.
            Reset the GUI search widgets and all current state afterwards. """
        self._dicts.new("strokes", d)
        self._dicts.new("translations", d, reverse=True)
        self._reset()
        return bool(d)

    @pipe("search_input", "new_search_matches")
    def on_input(self, pattern:str, match_pages:int=1) -> tuple:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        self._last_input = pattern
        self._pages = match_pages
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        matches = self._search() if pattern else []
        # If there's only one match and it's new, select it and continue as if the user had done it.
        if len(matches) == 1 and matches[0] != self._last_match:
            selection = matches[0]
            self.engine_call("search_choose_match", selection)
        else:
            # Otherwise, the match selection isn't changed and the previous mappings list must be cleared.
            selection = None
            self.engine_call("new_search_mappings", [], "")
        # Show the list of results, even if the list is empty.
        return matches, selection

    @pipe("search_choose_match", "new_search_mappings")
    def on_choose_match(self, match:str) -> Optional[tuple]:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        # If the user clicked "more", increment the page and add to the results list. Do not find a mapping.
        if match == _MORE_TEXT:
            self.engine_call("search_input", self._last_input, self._pages + 1)
            return
        self._last_match = match
        # Display the mapping results list and begin analysis.
        m_list = self._dicts.get_list(match)
        # It shouldn't be possible to fail a search on a listed match, but if it happens, just clear the list.
        if not m_list:
            return [], None
        if len(m_list) == 1:
            # With one mapping (any mode), select it and continue as if the user had done it.
            selection = m_list[0]
            self.on_choose_mapping(selection)
            # The mapping may be a rule. To be safe, show the string form of whatever it is.
            s = str(selection)
            return [s], s
        else:
            # If there is more than one mapping (only in word mode), make a lexer query to select the best one.
            assert not self._mode_strokes
            result = self.engine_call("lexer_query_product", m_list, [self._last_match])
            # Parse the rule's keys back into RTFCRE form and try to select that string in the list. """
            return m_list, result.keys.rtfcre

    @on("search_choose_mapping")
    def on_choose_mapping(self, mapping:str) -> None:
        """ For normal steno modes, make and send a lexer query based on the last selected match and this mapping. """
        if not isinstance(mapping, str):
            # If the mapping is a rule, send it as direct output just like the lexer would and return.
            self.engine_call("new_lexer_result", mapping)
            return
        # The order of strokes/word depends on the mode. Neither may be empty.
        match = self._last_match
        query = (match, mapping) if self._mode_strokes else (mapping, match)
        if all(query):
            self.engine_call("lexer_query", *query)

    @pipe("search_mode_strokes", "search_input")
    def set_mode_strokes(self, enabled:bool) -> str:
        """ Set strokes mode and search for the previous text again. """
        self._mode_strokes = enabled
        return self._last_input

    @pipe("search_mode_regex", "search_input")
    def set_mode_regex(self, enabled:bool) -> str:
        """ Set regex mode and search for the previous text again. """
        self._mode_regex = enabled
        return self._last_input

    def _search(self) -> List[str]:
        """ Perform a special search for the last input under the current modes. """
        pattern = self._parse_last_input()
        # The match_limit is determined by the config setting and the number of "more" selections.
        count = self._pages * self.match_limit
        matches = self._dicts.search(pattern, count, self._mode_regex)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(_MORE_TEXT)
        return matches

    def _parse_last_input(self) -> str:
        """ Set the search dict ready to use based on the last input and mode flags. Return the last input.
            If the pattern starts with the special rules prefix, change to the rules dict and remove the prefix. """
        if self._last_input.startswith(_RULES_PREFIX):
            self._dicts.use_dict("rules")
            return self._last_input[len(_RULES_PREFIX):]
        self._dicts.use_dict("strokes" if self._mode_strokes else "translations")
        return self._last_input

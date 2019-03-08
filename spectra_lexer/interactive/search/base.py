from typing import List, Optional, Tuple

from spectra_lexer import Component
from spectra_lexer.interactive.search.steno_dict import StenoSearchDictionary

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class SearchEngine(Component):
    """ Provides steno translation search engine services to the GUI and lexer. """

    ROLE = "search"
    match_limit: int = Option("config", "search:match_limit", 100, "Maximum number of matches returned by a search.")

    _translations: StenoSearchDictionary  # Search dict between strokes <-> translations.
    _last_input: str = ""                 # Last known state of user textbox input.
    _last_match: str = ""                 # Last search match selected by the user in the list.
    _last_page: int = 0                   # Number of times user has clicked "more" without changing the input.
    _mode_strokes: bool = False           # If True, search for strokes instead of translations.
    _mode_regex: bool = False             # If True, perform search using regex characters.

    def __init__(self):
        super().__init__()
        self._translations = StenoSearchDictionary()

    def reset(self):
        """ Reset all current state. """
        self._last_input = self._last_match = ""
        self._last_page = 0
        self._mode_strokes = self._mode_regex = False

    @pipe("new_translations", "new_search_state")
    def set_translations(self, d:dict) -> bool:
        """ Create a master dictionary to search in either direction from the raw translations dict given.
            Reset the GUI search widgets and all current state afterwards. """
        self._translations = StenoSearchDictionary(d)
        self.reset()
        return bool(d)

    @on("search_input", "new_search_matches")
    def on_input(self, pattern:str, match_page:int=0) -> tuple:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        self._last_input = pattern
        self._last_page = match_page
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

    @on("search_choose_match", "new_search_mappings")
    def on_choose_match(self, match:str) -> Optional[tuple]:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        # If the user clicked "more", increment the page and add to the results list. Do not find a mapping.
        if match == _MORE_TEXT:
            self.engine_call("search_input", self._last_input, self._last_page + 1)
            return
        self._last_match = match
        # Display the mapping results list and begin analysis.
        m_list = self._translations.get(match, self._mode_strokes)
        # It shouldn't be possible to fail a search on a listed match, but if it happens, just clear the list.
        if not m_list:
            return [], None
        # If the results aren't a list (strokes mode), make it one.
        if not isinstance(m_list, list):
            m_list = [m_list]
        if len(m_list) == 1:
            # With one mapping (either mode), make a regular query with that mapping and the last match.
            selection = m_list[0]
            self.on_choose_mapping(selection)
        else:
            # If there is more than one mapping (only in word mode), make a lexer query to select the best one.
            assert not self._mode_strokes
            result = self.engine_call("lexer_query_product", m_list, [self._last_match])
            # Parse the rule's keys back into RTFCRE form and try to select that string in the list. """
            selection = result.keys.rtfcre
        return m_list, selection

    @on("search_choose_mapping")
    def on_choose_mapping(self, mapping:str) -> Optional[Tuple[str, str]]:
        """ Make and send a lexer query based on the last selected match and this mapping (if non-empty). """
        match = self._last_match
        if not match or not mapping:
            return
        # The order of strokes/word depends on the mode.
        strokes, word = (match, mapping) if self._mode_strokes else (mapping, match)
        self.engine_call("lexer_query", strokes, word)

    @on("search_mode_strokes", "search_input")
    def set_mode_strokes(self, enabled:bool) -> str:
        """ Set strokes mode and search for the previous text again. """
        self._mode_strokes = enabled
        return self._last_input

    @on("search_mode_regex", "search_input")
    def set_mode_regex(self, enabled:bool) -> str:
        """ Set regex mode and search for the previous text again. """
        self._mode_regex = enabled
        return self._last_input

    def _search(self) -> List[str]:
        """ Perform a special search for the last input under the current modes.
            The match_limit is determined by the config setting and the number of "more" selections. """
        count = (self._last_page + 1) * self.match_limit
        matches = self._translations.search(self._last_input, count, self._mode_strokes, self._mode_regex)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(_MORE_TEXT)
        return matches

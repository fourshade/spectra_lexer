from typing import Dict

from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.rules import StenoRule

from spectra_lexer.search.steno_dict import CompositeSearchDictionary


class SearchEngine(SpectraEngineComponent):
    """ Main search class for finding strokes and translations that are similar to one another. """

    _dict: CompositeSearchDictionary  # Current search dict (contains both forward and reverse dicts)
    _last_pattern: str = ""           # Last detected text in the search box.
    _last_match: str = ""             # Last search match selected by the user in the list.

    def __init__(self):
        self._dict = CompositeSearchDictionary({})

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {"new_window":               self.on_new_window,
                "search_set_dict":          self.set_dict,
                "search_query":             self.on_search,
                "search_choose_match":      self.on_choose_match,
                "search_choose_mapping":    self.on_choose_mapping,
                "search_set_stroke_search": self.on_set_mode_strokes,
                "search_set_regex_enabled": self.on_set_mode_regex,
                "display_rule":             self.on_lexer_finished,}

    def on_new_window(self) -> None:
        """ After opening a new window, clear everything and enable
            searching only if there is a search dictionary loaded. """
        self._last_pattern = self._last_match = ""
        self._dict.mode_strokes = self._dict.mode_regex = False
        self.engine_send("gui_reset_search", bool(self._dict))

    def set_dict(self, src_dict:Dict[str, str]) -> None:
        """ Create the search dictionary from the raw steno dictionary given.
            Reset everything GUI-related afterwards. """
        self._dict = CompositeSearchDictionary(src_dict)
        self.on_new_window()

    def on_search(self, pattern:str) -> None:
        """ Look up a pattern in the dictionary and populate the matches list. """
        # Store this pattern in case we need it again before the user types more characters.
        self._last_pattern = pattern
        # The mappings list is always invalidated when the matches list is updated, so clear it.
        self.engine_send("gui_set_mapping_list", [])
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            self.engine_send("gui_set_match_list", [])
            return
        # Choose the right type of search based on the mode flags, execute it, and send the list to the GUI.
        matches = self._dict.search(pattern)
        self.engine_send("gui_set_match_list", matches)
        # If there's only one match and it's new, select it and begin analysis.
        if len(matches) == 1 and matches[0] != self._last_match:
            self.engine_send("gui_select_match", 0)
            self.on_choose_match(matches[0])

    def on_choose_match(self, match:str) -> None:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        self._last_match = match
        mapping_or_list = self._dict.get(match)
        if not mapping_or_list:
            return
        # We now have either a non-empty string (stroke mode) or a non-empty list of strings (word mode).
        # In either case, display the mapping results in list form and begin analysis.
        m_list = [mapping_or_list] if self._dict.mode_strokes else mapping_or_list
        self.engine_send("gui_set_mapping_list", m_list)
        # With one mapping (either mode), it is a regular query with a defined stroke and word.
        if len(m_list) == 1:
            self.engine_send("gui_select_mapping", 0)
            self.on_choose_mapping(m_list[0])
            return
        # If there is more than one mapping (only in word mode), make a lexer query to select the best one.
        self.engine_send("lexer_query_all", m_list, match)

    def on_choose_mapping(self, mapping:str) -> None:
        """ Make and send a lexer query based on the last selected match and this mapping (if non-empty). """
        match = self._last_match
        if not match or not mapping:
            return
        # The order of strokes/word depends on the mode.
        strokes, word = (match, mapping) if self._dict.mode_strokes else (mapping, match)
        self.engine_send("lexer_query", strokes, word)

    def on_set_mode_strokes(self, enabled:bool=True) -> None:
        """ Switch to strokes or text mode, then start a new search to overwrite the previous one. """
        self._dict.mode_strokes = enabled
        self.on_search(self._last_pattern)

    def on_set_mode_regex(self, enabled:bool) -> None:
        """ Set regex enabled or disabled. In either case, start a new search to overwrite the previous one. """
        self._dict.mode_regex = enabled
        self.on_search(self._last_pattern)

    def on_lexer_finished(self, result:StenoRule) -> None:
        """ If the lexer's output contains a mapping from our list, select it, else do nothing. """
        mapping = result.letters if self._dict.mode_strokes else result.keys.inv_parse()
        self.engine_send("gui_select_mapping", mapping)

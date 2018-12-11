import re
from typing import Dict, List

from spectra_lexer import SpectraComponent
from spectra_lexer.search.key_search import StringSearchDict
from spectra_lexer.search.steno_search import BidirectionalStenoSearchDict

# Hard limit on the number of matches returned by a special search.
_MATCH_LIMIT = 100


class SearchEngine(SpectraComponent):
    """ Main search class for finding strokes and translations that are similar to one another. """

    _dict: BidirectionalStenoSearchDict  # Current search dict (contains both forward and reverse dicts)
    _last_pattern: str = ""              # Last detected text in the search box.
    _last_match: str = ""                # Last search match selected by the user in the list.
    _mode_strokes: bool = False          # If True, use the forward dict, else use the reverse dict.
    _mode_regex: bool = False            # If True, treat search text input as a regular expression.

    def __init__(self):
        """ Initialize the base dict with the search function and any given arguments. """
        self._dict = BidirectionalStenoSearchDict()

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "new_window":               self.on_new_window,
                "new_search_dict":          self.set_dict,
                "search_query":             self.on_search,
                "search_choose_match":      self.on_choose_match,
                "search_choose_mapping":    self.on_choose_mapping,
                "search_set_stroke_search": self.on_set_mode_strokes,
                "search_set_regex_enabled": self.on_set_mode_regex}

    def on_new_window(self) -> None:
        """ After opening a new window, clear everything and enable
            searching only if there is a search dictionary loaded. """
        self._last_pattern = self._last_match = ""
        self._mode_strokes = self._mode_regex = False
        self.engine_call("gui_reset_search", bool(self._dict))

    def set_dict(self, src_dict:Dict[str, str]) -> None:
        """ Create the search dictionary from the raw steno dictionary given. """
        # TODO: Reset everything GUI-related afterwards.
        self._dict.clear()
        self._dict.update(src_dict)

    def on_search(self, pattern:str) -> None:
        """ Look up a pattern in the dictionary and populate the matches list. """
        # Store this pattern in case we need it again before the user types more characters.
        self._last_pattern = pattern
        # The mappings list is always invalidated when the matches list is updated, so clear it.
        self.engine_call("gui_set_mapping_list", [])
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            self.engine_call("gui_set_match_list", [])
            return
        # Choose the right type of search based on the mode flags, execute it, and send the list to the GUI.
        matches = self._search(self._raw_dict(),pattern)
        self.engine_call("gui_set_match_list", matches)
        # If there's only one match and it's new, select it and begin analysis.
        if len(matches) == 1 and matches[0] != self._last_match:
            self.engine_call("gui_select_match", 0)
            self.on_choose_match(matches[0])

    def on_choose_match(self, match:str) -> None:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        self._last_match = match
        mapping_or_list = self._raw_dict().get(match)
        if not mapping_or_list:
            return
        # We now have either a non-empty string (stroke mode) or a non-empty list of strings (word mode).
        # In either case, display the mapping results in list form and begin analysis.
        m_list = [mapping_or_list] if self._mode_strokes else mapping_or_list
        self.engine_call("gui_set_mapping_list", m_list)
        # With one mapping (either mode), it is a regular query with a defined stroke and word.
        if len(m_list) == 1:
            self.engine_call("gui_select_mapping", 0)
            self.on_choose_mapping(m_list[0])
            return
        # If there is more than one mapping (only in word mode), make a lexer query to select the best one.
        result = self.engine_call("app_query_and_display_best", m_list, match)
        # If the lexer's output contains a mapping from our list, select it.
        mapping = result.letters if self._mode_strokes else result.keys.inv_parse()
        self.engine_call("gui_select_mapping", mapping)

    def on_choose_mapping(self, mapping:str) -> None:
        """ Make and send a lexer query based on the last selected match and this mapping (if non-empty). """
        match = self._last_match
        if not match or not mapping:
            return
        # The order of strokes/word depends on the mode.
        strokes, word = (match, mapping) if self._mode_strokes else (mapping, match)
        self.engine_call("app_query_and_display", strokes, word)

    def on_set_mode_strokes(self, enabled:bool=True) -> None:
        """ Switch to strokes or text mode, then start a new search to overwrite the previous one. """
        self._mode_strokes = enabled
        self.on_search(self._last_pattern)

    def on_set_mode_regex(self, enabled:bool) -> None:
        """ Set regex enabled or disabled. In either case, start a new search to overwrite the previous one. """
        self._mode_regex = enabled
        self.on_search(self._last_pattern)

    def _raw_dict(self) -> StringSearchDict:
        return self._dict if self._mode_strokes else self._dict.reverse

    def _search(self, d:StringSearchDict, pattern:str, count:int=_MATCH_LIMIT) -> List[str]:
        """
        Perform a special search in the current direction (for strokes given a translation
        or translations given a stroke) and return a list of matches.

        pattern: Text pattern to match.
        count: Maximum number of matches to return.
        """
        if self._mode_regex:
            try:
                return d.regex_match_keys(pattern, count)
            except re.error:
                return ["REGEX ERROR"]
        else:
            return d.prefix_match_keys(pattern, count)

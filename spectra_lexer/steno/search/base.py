from typing import Optional

from .collection import MasterSearchDictionary
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class SearchEngine(Component):
    """ Provides steno translation search engine services to the GUI and lexer. """

    match_limit = Option("config", "search:match_limit", 100, "Maximum number of matches returned by a search.")

    _dict: MasterSearchDictionary  # Search dicts between strokes <-> translations.
    _pages: int                    # Number of pages of search results (each has <match_limit> results).
    _last_input: str               # Last known state of user textbox input.
    _last_mappings: list

    def __init__(self):
        super().__init__()
        self._dict = MasterSearchDictionary()
        self.reset()

    set_index = on("new_index")(delegate_to("_dict"))
    set_rules = on("new_rules")(delegate_to("_dict"))
    set_translations = pipe("new_translations", "new_search_state")(delegate_to("_dict"))
    set_mode_strokes = pipe("search_mode_strokes", "search_repeat")(delegate_to("_dict"))
    set_mode_regex = pipe("search_mode_regex", "search_repeat")(delegate_to("_dict"))

    @on("new_search_state")
    def reset(self, *args) -> None:
        """ Reset most of the current state. """
        self._pages = 1
        self._last_input = ""
        self._last_mappings = []

    @pipe("search_repeat", "new_search_matches")
    def search(self, pattern:str=None) -> tuple:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        if pattern is None:
            pattern = self._last_input
        self._last_input = pattern
        # The mappings list is always invalidated.
        self.engine_call("new_search_mappings", [], "")
        # If the pattern is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            return [], None
        # The match_limit is determined by the config setting and the number of "more" selections.
        count = self._pages * self.match_limit
        matches = self._dict.search(pattern, count)
        # If we met the count, add a final item to allow search expansion.
        if len(matches) == count:
            matches.append(_MORE_TEXT)
        return matches, None

    @pipe("search_input", "new_search_matches")
    def on_input(self, pattern:str=None) -> tuple:
        """ With new input, reset the page count and possibly select a match if there's only one. """
        matches, _ = self.search(pattern)
        self._pages = 1
        if len(matches) == 1:
            selection = matches[0]
            self.engine_call("search_choose_match", selection)
            return matches, selection
        return matches, None

    @pipe("search_choose_match")
    def on_choose_match(self, match:str) -> Optional[tuple]:
        """ When a match is chosen from the upper list, look up its mappings and display them in the lower list. """
        # If the user clicked "more", increment the page and add to the results list. Do not find a mapping.
        if match == _MORE_TEXT:
            self._pages += 1
            self.engine_call("search_repeat")
            return
        mappings = self._last_mappings = self._dict.lookup(match)
        if not mappings:
            self.engine_call("new_search_mappings", [], "")
            return
        if len(mappings) == 1:
            # A lone mapping should be removed from the list and sent on its own.
            # It may also be a rule. To be safe, show the string form of whatever it is.
            mappings = mappings[0]
            self.engine_call("new_search_mappings", [str(mappings)])
        else:
            self.engine_call("new_search_mappings", mappings)
        self.on_choose_mapping(mappings)

    @on("search_choose_mapping")
    def on_choose_mapping(self, mapping:object) -> None:
        """ Make and send a lexer query based on the last selected match and this mapping (or a list). """
        query = self._dict.get_query(mapping)
        if query is not None:
            self.engine_call(*query)

    @on("new_lexer_result", "new_search_mappings")
    def lexer_result(self, result) -> tuple:
        # Look for a relevant string in the mapping list and select it.
        for choice in (result.keys.rtfcre, result.letters, result):
            if choice in self._last_mappings:
                return None, str(choice)


from .collection import SearchDictionary
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.utils import delegate_to

# Text displayed as the final list item, allowing the user to expand the search.
_MORE_TEXT = "(more...)"


class SearchEngine(Component):
    """ Provides GUI support services for search. """

    match_limit = Option("config", "search:match_limit", 100, "Maximum number of matches returned by a search.")

    _dictionary: SearchDictionary  # Runs the actual search queries
    _count: int                    # Limit on number of search results. May exceed <match_limit> on user action.
    _mode_strokes: bool = False    # If True, search for strokes instead of translations.
    _mode_regex: bool = False      # If True, perform search using regex characters.
    _last_pattern: str = ""        # Last pattern from user textbox input.
    _last_match: str = ""          # Last selected match from the upper list.
    _last_mapping: str = ""        # Last selected mapping from the lower list.

    def __init__(self):
        super().__init__()
        self._dictionary = SearchDictionary()
        self._reset_count()

    def _reset_count(self) -> None:
        self._count = self.match_limit

    def _add_page_to_count(self) -> None:
        self._count += self.match_limit

    @pipe("start", "new_search_state")
    def start(self) -> bool:
        """ Turn on the GUI panel once everything is set up here. """
        return True

    @on("search_mode_strokes")
    def set_mode_strokes(self, enabled:bool) -> None:
        """ Set strokes search mode on or off and retry the last search. """
        self._mode_strokes = enabled
        self._repeat_search()

    @on("search_mode_regex")
    def set_mode_regex(self, enabled:bool) -> None:
        """ Set whether or not searches treat input queries as regular expressions and retry the last search. """
        self._mode_regex = enabled
        self._repeat_search()

    @on("search_input")
    def on_input(self, pattern:str) -> None:
        """ With new input, reset the search count and do a new search unless the input is blank. """
        self._reset_count()
        if pattern:
            self._new_search(pattern)

    def _new_search(self, pattern:str) -> None:
        self._last_pattern = pattern
        self._repeat_search()

    def _repeat_search(self) -> None:
        self.search(self._last_pattern, self._count, self._mode_strokes, self._mode_regex)

    def search(self, pattern:str, count:int=None, strokes:bool=False, regex:bool=False) -> list:
        """ Look up a pattern in the dictionary and populate the upper matches list. """
        matches = self._dictionary.search(pattern, count, strokes, regex)
        self._show_matches(matches)
        if len(matches) == 1:
            # Select the match if there was only one.
            self.engine_call("new_search_match_selection", matches[0])
            self._new_lookup(matches[0])
        return matches

    def _show_matches(self, matches:list) -> None:
        """ If we met the count, add a final item to allow search expansion. """
        if len(matches) == self._count:
            matches.append(_MORE_TEXT)
        # Show the new match list and wipe the mappings list.
        self.engine_call("new_search_match_list", matches)
        self.engine_call("new_search_mapping_list", [])

    @on("search_choose_match")
    def on_choose_match(self, match:str) -> None:
        """ When a match is chosen from the upper list, do a lookup after special checks. """
        if match == _MORE_TEXT:
            # If the user clicked "more", increment the count and search again. Do not find mappings.
            self._add_page_to_count()
            self._repeat_search()
        else:
            self._new_lookup(match)

    def _new_lookup(self, match:str) -> None:
        self._last_match = match
        self.lookup(match)

    def lookup(self, match:str) -> list:
        """ Look up mappings and display them in the lower list. """
        mappings = self._dictionary.lookup(match)
        self._show_mappings(mappings)
        if len(mappings) == 1:
            # A lone mapping should be selected manually and sent on its own.
            self.engine_call("new_search_mapping_selection", mappings[0])
            self._new_display(mappings[0])
        elif len(mappings) > 1:
            # We may not know which mapping will be chosen in the end, so we must save all possibilities.
            self._new_display(mappings)
        return mappings

    def _show_mappings(self, mappings:list) -> None:
        """ Mappings may be rules. To be safe, show the string form of everything. """
        self.engine_call("new_search_mapping_list", list(map(str, mappings)))

    @on("search_choose_mapping")
    def on_choose_mapping(self, mapping:str) -> None:
        """ When a mapping is chosen from the lower list, send a display command. """
        self._new_display(mapping)

    def _new_display(self, mapping:object) -> None:
        self._last_mapping = mapping
        self.display(self._last_match, mapping)

    def display(self, match:str, mappings:object) -> None:
        """ Send an engine command to display the given match and mappings object, whatever they are. """
        cmd_args = self._dictionary.command_args(match, mappings)
        if cmd_args is not None:
            self.engine_call(*cmd_args)

    @on("new_output")
    def on_output(self, rule:StenoRule) -> None:
        """ Choose a relevant mapping (if any) from the given rule if our last search had several choices. """
        if self._last_mapping:
            common_items = {rule.keys.rtfcre, rule.letters, rule}.intersection(self._last_mapping)
            if common_items:
                self.engine_call("new_search_mapping_selection", str(common_items.pop()))

    set_index = on("new_index")(delegate_to("_dictionary.new", "index"))
    set_rules = on("new_rules")(delegate_to("_dictionary.new", "rules"))
    set_translations = on("new_translations")(delegate_to("_dictionary.new", "translations"))

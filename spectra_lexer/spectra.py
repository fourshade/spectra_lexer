from typing import Dict, Iterable

from spectra_lexer.display.cascaded_text import CascadedTextDisplayEngine, TextRuleInfo
from spectra_lexer.lexer.base import StenoLexer
from spectra_lexer.search.base import SearchEngine

class Spectra:

    _lexer: StenoLexer                          # Main lexer object.
    _search_engine: SearchEngine                # Main controller of search functionality and translation input.
    _display_engine: CascadedTextDisplayEngine  # Main controller of text graph and diagram output.

    _gui = None
    _search_mode_regex: bool = False            # If True, treat search text input as a regular expression.
    _last_pattern: str = ""                     # Last detected text in the search box.
    _last_word: str = ""                        # Last word selected by the user.
    _last_info: object = None                   # Most recent info object from a mouse move event (only ref matters).

    def __init__(self):
        self._lexer = StenoLexer()
        self._search_engine = SearchEngine()
        self._display_engine = CascadedTextDisplayEngine()

    def new_window(self, gui):
        """ When opening a new window, store the new window reference and automatically
            enable searching if there are entries in the current search dictionary. """
        self._gui = gui
        if self._search_engine:
            self._set_search_enabled(True)

    def set_search_dict(self, d:Dict[str, str]) -> None:
        """ Give the search engine a normal steno dictionary to format and use in search.
            The source dictionary must have both keys and values in string form at this point. """
        self._search_engine.set_dict(d)
        self._set_search_enabled(bool(d))

    def show_status_message(self, msg:str) -> None:
        """ Show a message in the title bar. """
        self._gui.w_title.setText(msg)

    def _set_search_enabled(self, enabled:bool) -> None:
        """ Clear all search fields, then enable/disable each one according to the argument (True/False). """
        self._gui.w_input.setPlaceholderText("Search...")
        for w in (self._gui.w_input, self._gui.w_words, self._gui.w_strokes):
            w.clear()
            w.setEnabled(enabled)

    def query(self, keys:str, word:str) -> None:
        """
        Event handler that performs a lexer query and formats the result for display.
        key_str:    String of RTFCRE steno keys with / for stroke separators.
        word:       String of English text.
        """
        result = self._lexer.parse(keys, word)
        self._display_engine.make_text_display(result)
        self._display_rule()
        # Send the full set of keys and description for the base rule to the info widgets.
        info = self._display_engine.get_base_info()
        self._display_info(info)

    def query_keep_best_stroke(self, key_str_list:Iterable[str], word:str) -> TextRuleInfo:
        """ Like the previous method, but queries from a list of stroke strings that each match the given word.
            We only get the results from the best stroke. Return its base info to the calling method as well. """
        result = self._lexer.parse_all(key_str_list, word)
        self._display_engine.make_text_display(result)
        self._display_rule()
        info = self._display_engine.get_base_info()
        self._display_info(info)
        return info





    # w_words.itemSelected
    def choose_word(self, word:str) -> None:
        """ Choose a word from the current list and populate the strokes list with its steno representations."""
        self._last_word = word
        s_list = self._search_engine.get_strokes(word) or []
        self._gui.w_strokes.set_items(s_list)
        if s_list:
            # If the word has at least one stroke mapping, make a lexer query to select the best one.
            info = self.query_keep_best_stroke(s_list, word)
            keys = info.keys.inv_parse()
            # If this set of keys is present in the strokes list (it should be unless inv_parse()
            # does something screwy), select it with suppression to avoid triggering another query.
            try:
                idx = s_list.index(keys)
            except ValueError:
                return
            self._gui.w_strokes.select(idx, suppress_event=True)

    # w_strokes.itemSelected
    def choose_stroke(self, stroke:str) -> None:
        """ Choose a stroke from the current list, and with the previously selected word, send a query signal. """
        if self._last_word and stroke:
            self.query(stroke, self._last_word)

    # w_regex.toggled
    def set_regex_enabled(self, enabled:bool) -> None:
        """ Set regex enabled or disabled. In either case, start a new search to overwrite the previous one. """
        self._search_mode_regex = enabled
        self.search(self._last_pattern)

    # w_input.textEdited
    def search(self, pattern:str) -> None:
        """ Look up a word in the dictionary and populate the word list with possibilities. """
        # Store this pattern in case we need it again before the user types more characters.
        self._last_pattern = pattern
        # The strokes list is always invalidated when the word list is updated, so clear it.
        self._gui.w_strokes.clear()
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            self._gui.w_words.clear()
            return
        # Choose the right type of search based on the value of the check box.
        results = self._search_engine.search(pattern, reverse=True, regex=self._search_mode_regex)
        self._gui.w_words.set_items(results)
        # If there's only one result, go ahead and select it to begin stroke analysis.
        if len(results) == 1:
            self._gui.w_words.select(0)





    # w_text.mouseover_text_graph
    def mouseover_text_graph(self, row:int, col:int) -> None:
        """ Update the rule display with new formatting for the rule at character (row, col), if any. """
        info = self._display_engine.get_info_at(col, row)
        # It's only worth updating the display if it's not the same info we just saw (and isn't None).
        if info is not None and info is not self._last_info:
            # Set the new formatting from the rule info.
            self._gui.w_text.format_text(info.format_info)
            # Send the given rule info to the info widgets.
            self._display_info(info)
            # Store the current info so we can avoid redraw.
            self._last_info = info

    def _display_rule(self) -> None:
        """ Send the last rule output to the text output widget. """
        self.show_status_message(self._display_engine.title)
        # Any applied formatting should be reset when new text is loaded.
        self._gui.w_text.reset_formatting()
        self._gui.w_text.set_output(self._display_engine.text)

    def _display_info(self, info:TextRuleInfo) -> None:
        """ Send the given rule info to the board info widgets. """
        self._gui.w_desc.setText(info.description)
        self._gui.w_board.show_keys(info.keys)

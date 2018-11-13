import re

from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QWidget

from spectra_lexer.gui_qt.input_widget_ui import Ui_InputWidget
from spectra_lexer.search import StenoSearchDict

# Hard limit on the number of words returned by a search.
WORD_SEARCH_LIMIT = 100


class InputWidget(QWidget, Ui_InputWidget):
    """
    Container widget that holds all lexer input elements.

    Children:
    w_input - QLineEdit, input box for the user to etner a search string.
    w_words - QListView, list box to show the word suggestions for the user's search.
    w_strokes - QListView, list box to show the possibilities for strokes that map to the chosen word.
    """

    _dictionary: StenoSearchDict  # Dictionary of all words mapped to lists of their corresponding strokes.
    _last_word: str               # Last word selected by the user.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._dictionary = StenoSearchDict()
        self._last_word = ""

    def set_dictionary(self, d:StenoSearchDict) -> None:
        """ Set the search dictionary and clear and enable all search fields/lists. """
        self._dictionary = d
        self.set_search_enabled(True)
        self.w_input.setPlaceholderText("Search...")

    def set_search_enabled(self, enabled:bool) -> None:
        """ Clear all search fields, then enable/disable each one according to the argument (True/False). """
        for w in (self.w_input, self.w_words, self.w_strokes):
            w.clear()
            w.setEnabled(enabled)

    def set_best_stroke(self, keys:str) -> None:
        """ Set a specific set of keys as the best match for the last query. If this set of keys is present
            in the strokes list, select it (and suppress events that would end up making another query). """
        word = self._last_word
        if word and word in self._dictionary:
            s_list = self._dictionary[word]
            test_keys = keys.upper().replace("-", "")
            for (i, k) in enumerate(s_list):
                if k.upper().replace("-", "") == test_keys:
                    self.w_strokes.select(i, suppress_event=True)
                    break

    # Signals
    querySelected = pyqtSignal([str, str])
    queryBestStroke = pyqtSignal(['PyQt_PyObject', str])

    # Slots
    @pyqtSlot(str)
    def lookup(self, pattern:str) -> None:
        """ Look up a word in the dictionary and populate the word list with possibilities. """
        # The strokes list is always invalidated when the word list is updated, so clear it.
        self.w_strokes.clear()
        # If the text box is blank, a search would return the entire dictionary, so don't bother.
        if not pattern:
            self.w_words.clear()
            return
        # Choose the right type of search based on the value of the check box. It will either be clear
        # (for case-insensitive partial matches) or set (for case-sensitive regex matches).
        if self.w_regex.isChecked():
            try:
                results = self._dictionary.regex_match_keys(pattern, WORD_SEARCH_LIMIT)
            except re.error:
                self.w_words.set_items(["REGEX ERROR"])
                return
        else:
            results = self._dictionary.prefix_match_keys(pattern, WORD_SEARCH_LIMIT)
        self.w_words.set_items(results)
        # If there's only one result, go ahead and select it to begin stroke analysis.
        if len(results) == 1:
            self.w_words.select(0)

    @pyqtSlot(str)
    def choose_word(self, word:str) -> None:
        """ Choose a word from the current list and populate the strokes list with its steno representations.
            If the word has at least one stroke mapping, make a lexer query to select the best one. """
        self._last_word = word
        if word in self._dictionary:
            s_list = self._dictionary[word]
            self.w_strokes.set_items(s_list)
            if s_list:
                self.queryBestStroke.emit(s_list, word)

    @pyqtSlot(str)
    def choose_stroke(self, stroke:str) -> None:
        """ Choose a stroke from the current list, and with the previously selected word, send a query signal. """
        if self._last_word and stroke:
            self.querySelected.emit(stroke, self._last_word)

    @pyqtSlot(bool)
    def set_regex(self, enabled:bool) -> None:
        """ Set regex enabled or disabled. Since the widget state itself is read during search,
            this just starts a new search to overwrite the previous one. """
        self.lookup(self.w_input.text())

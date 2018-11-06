from typing import Collection, ClassVar, Dict

from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import QWidget

from spectra_lexer.gui_qt.main_widget_ui import Ui_MainWidget
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.search import ReverseStenoDict


class MainWidget(QWidget, Ui_MainWidget):
    """
    Main widget container for all GUI elements, and the main nexus of lexer operations.

    Children:
    w_input - InputWidget, allows the user to search for steno mappings.
    w_output - OutputWidget, responds to lexer queries (from Plover or user search).
    """

    # Instance attributes are lost when the container dialog is closed and re-opened.
    # These are relatively expensive to create, so save them on the class to retain their state.
    _lexer: ClassVar[StenoLexer] = StenoLexer()             # Main lexer object.
    _dict: ClassVar[ReverseStenoDict] = ReverseStenoDict()  # Main search dict object.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        if self._dict:
            self.w_input.set_dictionary(self._dict)

    def set_dictionary(self, d:Dict[str, str], load_msg:str="") -> None:
        """ Create a new steno dictionary for the input widget. Show a loading message if given.
            The source dictionary must have both keys and values in string form at this point. """
        if d:
            MainWidget._dict = ReverseStenoDict(d)
            self.w_input.set_dictionary(self._dict)
            if load_msg:
                self.w_output.show_message(load_msg)

    # Slots
    @pyqtSlot(str, str)
    def query(self, keys:str, word:str) -> None:
        """
        Event handler that performs a lexer query and sends the result to the format widget.
        key_str:    String of steno keys with / for stroke separators.
        word:       String of English text.
        """
        result = self._lexer.parse(keys, word)
        self.w_output.send_output(result)

    @pyqtSlot('PyQt_PyObject', str)
    def query_best(self, key_str_list:Collection[str], word:str) -> None:
        """ Like the previous method, but queries from a list of strokes that each match the given word.
            We only get the results from the best stroke. Send its keys to the input widget as well. """
        result = self._lexer.parse(key_str_list, word)
        self.w_input.set_best_stroke(result.keys)
        self.w_output.send_output(result)

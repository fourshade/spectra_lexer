from typing import ClassVar

from PyQt5.QtWidgets import QWidget, QLineEdit

from spectra_lexer.gui_qt.search_list_widget import SearchListWidget
from spectra_lexer.gui_qt.steno_board_widget import StenoBoardWidget
from spectra_lexer.gui_qt.text_graph_widget import TextGraphWidget
from spectra_lexer.spectra import Spectra
from spectra_lexer.gui_qt.main_widget_ui import Ui_MainWidget

class MainWidget(QWidget, Ui_MainWidget):
    """
    Main widget container for all GUI elements and the initial recipient of all GUI callbacks.

    Interactive children:
        Input:
            w_input   - QLineEdit, input box for the user to etner a search string.
            w_words   - QListView, list box to show the word suggestions for the user's search.
            w_strokes - QListView, list box to show the possibilities for strokes that map to the chosen word.
        Output:
            w_title - QLineEdit, displays status messages and mapping of keys to word.
            w_text  - QTextEdit, displays formatted text breakdown graph.
            w_desc  - QLineEdit, displays rule description.
            w_board - QWidget, displays steno board diagram.
    """

    # Instance attributes are lost when the container dialog is closed and re-opened.
    # The engine is relatively expensive to create, so save it on the class to retain its state.
    _engine: ClassVar[Spectra] = Spectra()

    def __init__(self, *args, **kwargs):
        """ Since the engine could have a reference to an old window, we must tell it this window is new. """
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        self._engine.new_window(self)

    def __getattr__(self, attr):
        """ Any Qt slot calls not defined here (which is all of them at present) get referred to the engine. """
        return getattr(self._engine, attr)


class SearchHandler:
    def __init__(self, w_input:QLineEdit, w_primary:SearchListWidget, w_secondary:SearchListWidget):
        pass


class DisplayHandler:
    def __init__(self, w_graph:TextGraphWidget, w_board:StenoBoardWidget, w_desc:QLineEdit):
        pass

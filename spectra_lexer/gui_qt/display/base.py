from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer.gui_qt import GUIQtComponent
from spectra_lexer.gui_qt.display.steno_board_widget import StenoBoardWidget
from spectra_lexer.gui_qt.display.text_graph_widget import TextGraphWidget


class GUIQtDisplay(GUIQtComponent):
    """ GUI operations class for displaying rules and finding the mouse position over the text graph. """

    w_title: QLineEdit         # Displays status messages and mapping of keys to word.
    w_text: TextGraphWidget    # Displays formatted text breakdown graph.
    w_desc: QLineEdit          # Displays rule description.
    w_board: StenoBoardWidget  # Displays steno board diagram.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_title, self.w_text, self.w_desc, self.w_board = widgets

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "gui_display_title": self.w_title.setText,
                "gui_display_graph": self.w_text.set_graph,
                "gui_display_info":  self.display_info}

    def on_new_window(self) -> None:
        """ Clear the display so that old output isn't drawn on the new window. """
        super().on_new_window()
        self.engine_call("display_clear")

    def engine_slots(self) -> dict:
        """ Individual components must define the slots they handle and the appropriate commands or callbacks. """
        return {**super().engine_slots(),
                self.w_text.mouseOverCharacter: "display_info_at"}

    def display_info(self, keys:str, desc:str) -> None:
        """ Send the given rule info to the board info widgets. """
        self.w_desc.setText(desc)
        self.w_board.show_keys(keys)

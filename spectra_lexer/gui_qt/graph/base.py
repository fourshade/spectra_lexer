from functools import partial

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.graph.text_graph_widget import TextGraphWidget


class GUIQtTextDisplay(Component):
    """ GUI operations class for displaying status and text graphs, and finding the mouse position by character. """

    ROLE = "gui_text"

    w_title: QLineEdit       # Displays status messages and mapping of keys to word.
    w_text: TextGraphWidget  # Displays formatted text breakdown graph.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_title, self.w_text = widgets

    @on("start")
    def start(self, **opts) -> None:
        """ Connect the mouse signal to the graph. """
        self.w_text.mouseInteraction.connect(partial(self.engine_call, "graph_select"))

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the title bar. """
        self.w_title.setText(msg)

    @on("new_graph_text")
    def display_graph(self, text:str, **kwargs) -> None:
        """ Display a finished interactive HTML text graph in the main text widget and enable mouse events. """
        self.w_text.set_interactive_text(text, html=True, mouse=True, **kwargs)

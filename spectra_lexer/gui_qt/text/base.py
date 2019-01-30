from functools import partial

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on, pipe
from spectra_lexer.gui_qt.text.text_graph_widget import TextGraphWidget


class GUIQtTextDisplay(Component):
    """ GUI operations class for displaying text graphs and finding the mouse position by character.
        Also displays engine output such as status messages and provides an output surface for exceptions. """

    ROLE = "gui_text"

    w_title: QLineEdit         # Displays status messages and mapping of keys to word.
    w_text: TextGraphWidget    # Displays formatted text breakdown graph.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_title, self.w_text = widgets

    @on("start")
    def start(self, **opts) -> None:
        """ Register the mouseover signal. Keyboard input may also be available from this widget in the future. """
        self.w_text.mouseOverCharacter.connect(partial(self.engine_call, "sig_process_mouseover"))

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the title bar. """
        self.w_title.setText(msg)

    @on("new_graph")
    def display_new_graph(self, text:str, **kwargs) -> None:
        """ Display a finished interactive HTML text graph in the main text widget. """
        self.w_text.set_text_display(text, html=True, interactive=True, **kwargs)

    @on("new_text_output")
    def display_new_text(self, text:str, **kwargs) -> None:
        """ Display non-interactive plaintext in the main text widget. Use if text is too long for the title bar. """
        self.w_text.set_text_display(text, html=False, interactive=False,  **kwargs)

    @pipe("sig_process_mouseover", "graph_select", unpack=True)
    def process_mouseover(self, row:int, col:int) -> tuple:
        """ Pass a mouseover event to the graph formatter. Switch the arguments to put it in (x, y) order. """
        return col, row

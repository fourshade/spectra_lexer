from functools import partial

from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import Component, on
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
        """ Connect the keyboard and mouse signals to the console and graph respectively. """
        self.w_text.textInputComplete.connect(partial(self.engine_call, "console_input"))
        self.w_text.mouseInteraction.connect(partial(self.engine_call, "graph_select"))

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the title bar. """
        self.w_title.setText(msg)

    @on("new_exception_text")
    def display_exception(self, text:str) -> None:
        """ Display an exception traceback in plaintext with no interaction flags. """
        self.w_text.set_text(text)

    @on("new_graph_text")
    def display_graph(self, text:str, **kwargs) -> None:
        """ Display a finished interactive HTML text graph in the main text widget and enabled mouse events. """
        self.w_text.set_interactive_text(text, html=True, mouse=True, **kwargs)

    @on("new_console_text")
    def display_console(self, text:str, **kwargs) -> None:
        """ Display a new window of console output plaintext in the main text widget and start accepting input. """
        self.w_text.set_interactive_text(text, keyboard=True, **kwargs)

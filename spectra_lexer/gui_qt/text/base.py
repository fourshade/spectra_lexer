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
        """ Register the keyboard and mouse input signals. """
        self.w_text.textInputComplete.connect(partial(self.engine_call, "sig_process_keyboard"))
        self.w_text.mouseInteraction.connect(partial(self.engine_call, "sig_process_mouse"))

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

    @pipe("sig_process_keyboard", "console_input")
    def process_keyboard(self, text:str) -> str:
        """ Pass a keyboard input event to the console. """
        return text

    @pipe("sig_process_mouse", "graph_select", unpack=True)
    def process_mouse(self, row:int, col:int, clicked:bool) -> tuple:
        """ Pass a mouseover/click event to the graph formatter. Switch the arguments to put it in (x, y) order. """
        return col, row, clicked

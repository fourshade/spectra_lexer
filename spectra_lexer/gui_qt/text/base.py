from functools import partial
import sys
from traceback import TracebackException

from PyQt5.QtWidgets import QLineEdit, QWidget

from .text_graph_widget import TextGraphWidget
from spectra_lexer import Component


class GUIQtTextDisplay(Component):
    """ GUI operations class for displaying status, interactive text, and exceptions.
        Also handles keyboard and mouse input to the text widget. """

    w_title: QLineEdit = None       # Displays status messages and mapping of keys to word.
    w_text: TextGraphWidget = None  # Displays formatted rule graphs and other textual data.

    @on("new_gui_text")
    def new_gui(self, *widgets:QWidget) -> None:
        """ Save the required widgets and connect the keyboard and mouse signals to the main text window. """
        self.w_title, self.w_text = widgets
        self.w_text.textMouseAction.connect(partial(self.engine_call, "text_mouse_action"))
        self.w_text.textKeyboardInput.connect(partial(self.engine_call, "text_keyboard_input"))

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the title bar. """
        self.w_title.setText(msg)

    @on("new_interactive_text")
    def display_graph(self, text:str, **kwargs) -> None:
        """ Display a block of interactive text in the main text widget and enable or disable events. """
        self.w_text.set_interactive_text(text, **kwargs)

    @on("new_exception")
    def handle_exception(self, e:Exception) -> bool:
        """ The stack trace for unhandled exceptions is displayed in plaintext with no interaction flags.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        if self.w_text is not None:
            self.w_text.set_interactive_text(tb_text)
        return True

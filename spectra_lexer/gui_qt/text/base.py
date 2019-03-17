from functools import partial

from PyQt5.QtWidgets import QLineEdit, QWidget

from .text_graph_widget import TextGraphWidget
from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


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

    set_title = on("new_title_text")(delegate_to("w_title.setText"))

    set_interactive_text = on("new_interactive_text")(delegate_to("w_text"))

from functools import partial

from PyQt5.QtWidgets import QWidget

from spectra_lexer import Component, on
from spectra_lexer.gui_qt.text.text_graph_widget import TextGraphWidget


class GUIQtConsoleDisplay(Component):
    """ GUI operations class for displaying console output and receiving text input from the keyboard. """

    ROLE = "gui_console"

    w_text: TextGraphWidget    # Displays console prompts, input, and output.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        _, self.w_text = widgets

    @on("start")
    def start(self, show_menu=True, **opts) -> None:
        """ Connect the keyboard signal to the console. If the menu is used, add the console dialog command. """
        self.w_text.textInputComplete.connect(partial(self.engine_call, "console_input"))
        if show_menu:
            self.engine_call("gui_menu_add", "Tools", "Open Console...", "console_open")

    @on("new_console_text")
    def display_console(self, text:str, **kwargs) -> None:
        """ Display a new window of console output plaintext in the main text widget and start accepting input. """
        self.w_text.set_interactive_text(text, keyboard=True, **kwargs)

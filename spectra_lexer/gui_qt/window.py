from .base import GUIQT
from .widgets import MainWindow


class QtWindow(GUIQT):
    """ GUI Qt operations class for the main window. """

    def Load(self) -> None:
        """ Connect and enable all GUI controls. """
        self._set_widgets()
        self.GUIQTConnect()
        self.GUIQTShowWindow()
        self.GUIQTSetEnabled(True)

    def _set_widgets(self) -> None:
        """ Create the window and map all Python widget classes to internal Qt Designer names. """
        window = self.WINDOW = MainWindow()
        self.W_MENU = window.m_menu
        self.W_BOARD = window.w_display_board
        self.W_DESC = window.w_display_desc
        self.W_TITLE = window.w_display_title
        self.W_TEXT = window.w_display_text
        self.W_INPUT = window.w_search_input
        self.W_MATCHES = window.w_search_matches
        self.W_MAPPINGS = window.w_search_mappings
        self.W_STROKES = window.w_search_type
        self.W_REGEX = window.w_search_regex

    def GUIQTShowWindow(self) -> None:
        self.WINDOW.show()

    def GUIQTCloseWindow(self) -> None:
        self.WINDOW.close()

    def GUIQTSetEnabled(self, enabled:bool) -> None:
        self.W_INPUT.clear()
        self.W_INPUT.setPlaceholderText("Search..." if enabled else "")
        self.W_MATCHES.clear()
        self.W_MAPPINGS.clear()
        self.W_BOARD.set_link("")
        self.W_INPUT.setEnabled(enabled)
        self.W_MATCHES.setEnabled(enabled)
        self.W_MAPPINGS.setEnabled(enabled)
        self.W_STROKES.setEnabled(enabled)
        self.W_REGEX.setEnabled(enabled)
        self.W_MENU.setEnabled(enabled)

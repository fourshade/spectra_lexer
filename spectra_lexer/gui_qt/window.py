from .base import GUIQT, MENU_ITEMS
from .widgets import MainWindow


class QtWindow(GUIQT):
    """ Qt operations class for the main window and menu. """

    _last_status: str = ""

    def Load(self) -> None:
        """ Create the window and connect all GUI controls.
            Display the last status if it occurred before connection. """
        self.WINDOW = MainWindow()
        self._set_widgets()
        self._set_menu()
        self.GUIQTConnect()
        self.GUIQTShowWindow()
        self.GUIQTSetEnabled(True)
        if self._last_status:
            self.W_TITLE.set_text(self._last_status)

    def _set_widgets(self) -> None:
        """ Map all Python widget classes to internal Qt Designer names. """
        window = self.WINDOW
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

    def _set_menu(self) -> None:
        """ Add new GUI menu items/separators with required headings as needed. """
        menu = self.W_MENU
        for heading, text, after_sep, cmd in MENU_ITEMS:
            if after_sep:
                menu.add_separator(heading)
            # Bind the command to this component and add a new menu item that calls it when selected.
            menu.add_item(heading, text, cmd.wrap(self))

    def GUIQTShowWindow(self) -> None:
        self.WINDOW.show()

    def GUIQTCloseWindow(self) -> None:
        self.WINDOW.close()

    def SYSStatus(self, status:str) -> None:
        """ Show engine status messages in the title as well. Save the last one in case we're not connected yet. """
        if self.W_TITLE is not None:
            self.W_TITLE.set_text(status)
        else:
            self._last_status = status

    def SYSTraceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget, if possible. """
        try:
            self.W_TITLE.set_text("Well, this is embarrassing...", dynamic=False)
            self.W_TEXT.set_plaintext(tb_text)
        except Exception:
            # The Qt GUI is probably what raised the error in the first place.
            # Re-raising will kill the program. Let lower-level handlers try first.
            pass

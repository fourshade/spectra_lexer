from .base import GUIQT
from .widgets import MainWindow


class QtWindow(GUIQT):
    """ Qt operations class for the main window and menu. """

    window: MainWindow = None  # Main GUI window. All GUI activity is coupled to this window.

    def Load(self) -> None:
        """ Create the window and connect all GUI controls. """
        window = self.window = MainWindow()
        # Map all Python widget classes to internal Qt Designer names.
        widgets = dict(w_menu=window.m_menu,
                       w_board=window.w_display_board,
                       w_desc=window.w_display_desc,
                       w_title=window.w_display_title,
                       w_text=window.w_display_text,
                       w_input=window.w_search_input,
                       w_matches=window.w_search_matches,
                       w_mappings=window.w_search_mappings,
                       w_strokes=window.w_search_type,
                       w_regex=window.w_search_regex)
        self.GUIQTConnect(window=window, **widgets)
        self.GUIQTShowWindow()
        self.GUIQTSetEnabled(True)

    def GUIQTShowWindow(self) -> None:
        self.window.show()

    def GUIQTCloseWindow(self) -> None:
        self.window.close()

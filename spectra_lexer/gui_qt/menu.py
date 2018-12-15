from PyQt5.QtWidgets import QAction, QMenu, QMenuBar, QWidget

from spectra_lexer.gui_qt import GUIQtComponent


class GUIQtMenu(GUIQtComponent):

    m_menu: QMenuBar      # Top-level widget for the entire menu bar.
    m_file: QMenu         # File submenu (no action by itself).
    m_file_load: QAction  # Load a new search dictionary set.
    m_file_exit: QAction  # Exit the program.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.m_menu, self.m_file, self.m_file_load, self.m_file_exit = widgets

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_commands(),
                "gui_menu_set_visible": self.m_menu.setVisible}

    def engine_slots(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks.
            Some commands have identical signatures to the Qt GUI methods; those can be passed directly. """
        return {**super().engine_slots(),
                self.m_file_load.triggered: "user_load_translations",
                self.m_file_exit.triggered: "close_window"}

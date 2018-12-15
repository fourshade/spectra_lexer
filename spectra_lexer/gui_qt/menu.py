from PyQt5.QtWidgets import QAction, QMenu, QMenuBar, QWidget

from spectra_lexer import SpectraComponent


class GUIQtMenu(SpectraComponent):
    """ GUI operations class for menu operations. Each action just consists of clicking a menu bar item. """

    m_menu: QMenuBar      # Top-level widget for the entire menu bar.
    m_file: QMenu         # File submenu (no action by itself).
    m_file_load: QAction  # Load a new search dictionary set.
    m_file_exit: QAction  # Exit the program.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.m_menu, self.m_file, self.m_file_load, self.m_file_exit = widgets
        self.m_file_load.triggered.connect(self.dialog_load)
        self.m_file_exit.triggered.connect(self.window_close)

    def dialog_load(self, *args):
        self.engine_call("window_dialog_load")

    def window_close(self, *args):
        self.engine_call("window_close")

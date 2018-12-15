from PyQt5.QtCore import pyqtSignal

from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.plover import PloverPluginLayer


class PloverWindow(MainWindow):
    """ See the breakdown of words using steno rules. """
    # Main QT application window as called from Plover. Must emulate a dialog type.

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, *args):
        """ Set up the application with the Plover interface and hide the menu bar. """
        super().__init__(PloverPluginLayer(*args))
        self.m_menu.hide()

    # To emulate a dialog class, this object must have a finished signal.
    finished = pyqtSignal([])

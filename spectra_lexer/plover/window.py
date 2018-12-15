from PyQt5.QtCore import pyqtSignal

from spectra_lexer.gui_qt.main_window import MainWindow


class PloverPluginWindow(MainWindow):
    """ Main QT application window as opened from Plover. Must emulate a dialog type. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self):
        """ Hide the menu bar so the window resembles a dialog (and can't load dictionaries from disk). """
        super().__init__()
        self.m_menu.hide()

    # To emulate a dialog class, this object must have a finished signal.
    finished = pyqtSignal([])

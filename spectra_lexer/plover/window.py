from PyQt5.QtCore import pyqtSignal

from spectra_lexer.gui_qt.window import BaseWindow


class PloverPluginWindow(BaseWindow):
    """ Main QT application window as opened from Plover. Must emulate a dialog type. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    # To emulate a dialog class, this object must have a finished signal.
    finished = pyqtSignal([])

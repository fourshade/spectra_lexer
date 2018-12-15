from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QCloseEvent, QShowEvent

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

    def __init__(self):
        """ Hide the menu bar so that the window looks more like a dialog (and can't load dictionaries from disk). """
        super().__init__()
        self.m_menu.setVisible(False)
        self.finished.connect(self.on_finished)

    def on_finished(self):
        self.engine_call("window_destroyed", self)

    # def showEvent(self, evt:QShowEvent):
    #     """ Send an engine command to connect the window's components upon visibility. """
    #     super().showEvent(evt)
    #     self.engine_call("window_opened", self)
    #
    # def closeEvent(self, evt:QCloseEvent) -> None:
    #     """ Send a final engine command to disconnect the window before disappearance or destruction. """
    #     super().closeEvent(evt)
    #     self.engine_call("window_closed", self)

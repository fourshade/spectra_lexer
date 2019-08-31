from typing import Callable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QWidget


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. Restricts subclasses to one instance each. """

    sig_accept = pyqtSignal([object])  # Signal to return config values to the parent on dialog accept.

    _LAST_INSTANCE: QDialog = None  # Most recent instance of a particular dialog subclass.
    _DIALOG_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint

    @classmethod
    def new(cls, parent:QWidget=None, *args, callback:Callable=None) -> None:
        """ Create a new UI dialog window, perform setup, connect the callback (if given), and display it.
            If a previous dialog instance exists, close it first and overwrite the reference (which may destroy it). """
        if cls._LAST_INSTANCE is not None:
            cls._LAST_INSTANCE.close()
        self = cls._LAST_INSTANCE = cls(parent, cls._DIALOG_FLAGS)
        self.setup(*args)
        if callback is not None:
            self.sig_accept.connect(callback)
        self.show()

    def setup(self, *args) -> None:
        """ Subclasses perform basic setup after construction here. """
        raise NotImplementedError

    def setup_window(self, title:str, width:int, height:int) -> None:
        """ Set the most basic properties of the window: the title string and its dimensions in pixels. """
        self.setWindowTitle(title)
        self.resize(width, height)
        self.setMinimumSize(width, height)
        self.setSizeGripEnabled(False)

    def button_box(self) -> QDialogButtonBox:
        """ Return a set of standard buttons connected to the basic dialog slots. """
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        w_buttons.setCenterButtons(True)
        w_buttons.accepted.connect(self.accept)
        w_buttons.rejected.connect(self.reject)
        return w_buttons

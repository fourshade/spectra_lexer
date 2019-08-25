from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QLayout, QWidget


class ToolDialog(QDialog):
    """ Base class for a Qt dialog window object used by a GUI tool. Restricts subclasses to one instance each. """

    TITLE: str = "Untitled"   # Dialog window title string.
    SIZE: tuple = (200, 200)  # Dimensions in pixels: (width, height).

    _LAST_INSTANCE: QDialog = None  # Most recent instance of a particular dialog subclass.

    def __new__(cls, *args, **kwargs):
        """ If a previous dialog instance exists, close it and overwrite the reference (which may destroy it). """
        if cls._LAST_INSTANCE is not None:
            cls._LAST_INSTANCE.close()
        self = cls._LAST_INSTANCE = super().__new__(cls, *args, **kwargs)
        return self

    def __init__(self, parent:QWidget) -> None:
        """ Create the root UI dialog window. """
        super().__init__(parent, Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle(self.TITLE)
        self.resize(*self.SIZE)
        self.setMinimumSize(*self.SIZE)
        self.setSizeGripEnabled(False)

    def add_buttons(self, layout:QLayout) -> None:
        """ Add standard buttons at the bottom of the given layout and connect them to the dialog. """
        w_buttons = QDialogButtonBox(self)
        w_buttons.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        w_buttons.setCenterButtons(True)
        w_buttons.accepted.connect(self.accept)
        w_buttons.rejected.connect(self.reject)
        layout.addWidget(w_buttons)

from PyQt5.QtCore import pyqtSignal, QEvent, QObject
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow


class WindowController(QObject):
    """ Wrapper class with methods for manipulating the main window. """

    activated = pyqtSignal()  # Emitted when the window state changes from inactive to active.

    def __init__(self, w_window:QMainWindow) -> None:
        super().__init__(w_window)
        self._w_window = w_window  # Main Qt window.
        w_window.installEventFilter(self)

    def eventFilter(self, _, event:QEvent) -> bool:
        if event.type() == QEvent.WindowActivate:
            self.activated.emit()
        return False

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus.
            These events should be explicitly processed before another thread can take the GIL. """
        self._w_window.show()
        self._w_window.activateWindow()
        self._w_window.raise_()
        QApplication.instance().processEvents()

    def close(self) -> None:
        self._w_window.close()

    def set_icon(self, data:bytes) -> None:
        """ Set the main window icon from a raw bytes object containing an image in some standard format.
            PNG and SVG formats are known to work. """
        pixmap = QPixmap()
        pixmap.loadFromData(data)
        icon = QIcon(pixmap)
        self._w_window.setWindowIcon(icon)

    def has_focus(self) -> bool:
        """ Return True if the window (or something in it) currently has keyboard focus. """
        return self._w_window.isActiveWindow()

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow


class WindowController:
    """ Wrapper class with methods for manipulating the main window. """

    def __init__(self, w_window:QMainWindow) -> None:
        self._w_window = w_window  # Main Qt window.

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

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow


class WindowController:
    """ Wrapper class with methods for manipulating the main window. """

    def __init__(self, w_window:QMainWindow) -> None:
        self._w_window = w_window  # Main Qt window.

    def load_icon(self, data:bytes) -> None:
        """ Load the main window icon from a bytes object. """
        im = QPixmap()
        im.loadFromData(data)
        icon = QIcon(im)
        self._w_window.setWindowIcon(icon)

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus. """
        self._w_window.show()
        self._w_window.activateWindow()
        self._w_window.raise_()

    def close(self) -> None:
        """ Close the main window. """
        self._w_window.close()

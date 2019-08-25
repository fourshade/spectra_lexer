from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow


class MainWindow(QMainWindow):
    """ Main GUI window. """

    def load_icon(self, data:bytes) -> None:
        """ Load the main window icon from a bytes object. """
        im = QPixmap()
        im.loadFromData(data)
        icon = QIcon(im)
        self.setWindowIcon(icon)

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus. """
        super().show()
        self.activateWindow()
        self.raise_()

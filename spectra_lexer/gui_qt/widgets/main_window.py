from PyQt5.QtWidgets import QMainWindow

from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for Qt application window as created from the command line script or Plover. """

    def __init__(self):
        """ Set up the main window. """
        super().__init__()
        self.setupUi(self)

    def show(self) -> None:
        super().show()
        self.activateWindow()
        self.raise_()

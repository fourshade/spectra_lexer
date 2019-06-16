from pkgutil import get_data

from PyQt5.QtWidgets import QMainWindow

from .main_window_ui import Ui_MainWindow
from ..icon import IconRenderer


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for Qt application window as created from the command line script or Plover. """

    def __init__(self):
        """ Set up the main window. """
        super().__init__()
        self.setupUi(self)
        icon_data = get_data(__package__, "icon.svg")
        icon = IconRenderer(icon_data).generate()
        self.setWindowIcon(icon)

    def show(self) -> None:
        super().show()
        self.activateWindow()
        self.raise_()

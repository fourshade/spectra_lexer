from typing import Dict, List

from PyQt5.QtWidgets import QMainWindow, QWidget

from .main_window_ui import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """ Base class for Qt application window as created from the command line script or Plover. """

    def __init__(self):
        """ Set up the main window. """
        super().__init__()
        self.setupUi(self)

    def widgets(self) -> Dict[str, List[QWidget]]:
        """ Return a dict of all widgets created by the generated Python code, as well as the window itself. """
        return {"window": self, **vars(self)}

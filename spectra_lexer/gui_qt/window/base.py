from .main_window import MainWindow
from spectra_lexer.gui import Window


class GUIQtWindow(Window):
    """ GUI Qt operations class for the main window. """

    window: MainWindow = None  # Main GUI window. All GUI activity (including dialogs) is coupled to this window.

    def __init__(self):
        self.window = MainWindow()

    def get_window_elements(self) -> dict:
        return self.window.widgets()

    def show(self):
        if self.window is not None:
            self.window.show()
            self.window.activateWindow()
            self.window.raise_()

    def close(self):
        if self.window is not None:
            self.window.close()

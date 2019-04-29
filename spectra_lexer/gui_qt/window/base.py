from .main_window import MainWindow
from spectra_lexer.gui import Window


class GUIQtWindow(Window):
    """ GUI Qt operations class for the main window. """

    window: MainWindow = None  # Main GUI window. All GUI activity (including dialogs) is coupled to this window.

    def __init__(self):
        self.window = MainWindow()

    @on("init:gui")
    @pipe_to("res:gui:")
    def start(self, keys:dict) -> dict:
        """ Get everything we need from the window and send it all to the GUI components. """
        elements = self.window.widgets()
        return {k: elements[k] for k in keys if k in elements}

    def show(self) -> None:
        if self.window is not None:
            self.window.show()
            self.window.activateWindow()
            self.window.raise_()

    def close(self) -> None:
        if self.window is not None:
            self.window.close()

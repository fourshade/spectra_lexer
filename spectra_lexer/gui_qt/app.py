import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.gui_qt.main_window import MainWindow


class GUIQtAppBase(SpectraApplication):
    """ Abstract base class for operation of the Spectra program with a GUI. """

    def new_window(self, window:MainWindow) -> None:
        """ Set up the window in a separate step. It may be destroyed and re-created independently.
            This may be called multiple times, with new windows overwriting old ones. """
        self.engine.connect(window, overwrite=True)
        window.show()
        # All engine components must reset (or initialize) their memory of the GUI state.
        self.engine_send("new_window")

    def engine_subcomponents(self) -> tuple:
        """ Default GUI support components. """
        return (*super().engine_subcomponents(), CascadedTextDisplay())


class GUIQtApplication(GUIQtAppBase):
    """ Top-level class for operation of the Spectra program by itself with the standard GUI. """

    def __init__(self, **kwargs) -> None:
        """ For standalone operation, a Qt application object must be created to support the windows. """
        app = QApplication(sys.argv)
        super().__init__(**kwargs)
        self.new_window(MainWindow())
        app.exec_()

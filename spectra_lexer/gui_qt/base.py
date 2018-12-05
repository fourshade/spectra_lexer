import sys
from typing import List, Type

from PyQt5.QtWidgets import QApplication

from spectra_lexer import SpectraApplication
from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.gui_qt.main_window import MainWindow

# Default GUI support components. Each must initialize with no arguments.
BASE_GUI_COMPONENTS:List[Type[SpectraEngineComponent]] = [CascadedTextDisplay]


class SpectraGUIQtBase(SpectraApplication):
    """ Abstract class for operation of the Spectra program with a GUI. """

    def __init__(self, **kwargs) -> None:
        """ Initialize the application with base components and keyword arguments from the caller. """
        super().__init__(**kwargs)
        self.engine.connect(*[cmp() for cmp in BASE_GUI_COMPONENTS])

    def new_window(self, window:MainWindow, *transient_components:SpectraEngineComponent) -> None:
        """ Set up the window with any transient components in a separate step.
            Transient components are those that live and die with the window.
            This may be called multiple times, with new components overwriting old ones. """
        self.engine.connect(*transient_components, window, overwrite=True)
        window.show()
        # All engine components must reset (or initialize) their memory of the GUI state.
        self.engine.send("new_window")


class SpectraGUIQtApplication(SpectraGUIQtBase):
    """ Top-level class for operation of the Spectra program by itself with the standard GUI. """

    def __init__(self, **kwargs) -> None:
        """ For standalone operation, a Qt application object must be created to support the windows. """
        app = QApplication(sys.argv)
        super().__init__(**kwargs)
        self.new_window(MainWindow())
        app.exec_()

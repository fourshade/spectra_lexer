import sys
from functools import partial

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.display.cascaded_text import CascadedTextDisplay
from spectra_lexer.gui_qt.window import BaseWindow, MainWindow


class GUIQtBaseApplication(SpectraApplication):
    """ Abstract base class for operation of the Spectra program with a GUI. """

    def new_window(self, window:BaseWindow) -> None:
        """ Set up the window in a separate step. It may be destroyed and re-created independently.
            This may be called multiple times, with new windows overwriting old ones. """
        self.engine.connect(window, overwrite=True)
        window.show()
        # All engine components must reset (or initialize) their memory of the GUI state.
        self.engine_call_async("new_window")

    def engine_commands(self) -> dict:
        """ Individual components must define the signals they respond to and the appropriate callbacks. """
        return {**super().engine_commands(),
                "close_window":               (lambda *args: sys.exit()),
                "user_load_translations":     self.dialog_load_translations,
                "dialog_translations_chosen": partial(self.load_translations_from, src_string="file dialog")}

    def engine_subcomponents(self) -> tuple:
        """ Default GUI support components. """
        return (*super().engine_subcomponents(), CascadedTextDisplay())

    def dialog_load_translations(self, *args) -> None:
        """ Present a dialog for the user to select one or more steno dictionary files.
            Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_dict_formats")
        fname = self.engine_call("gui_dialog_load_dict", file_formats)
        if fname:
            self.engine_call("dialog_translations_chosen", (fname,))


class GUIQtMainApplication(GUIQtBaseApplication):
    """ Top-level class for operation of the Spectra program by itself with the standard GUI. """

    def __init__(self, **kwargs) -> None:
        """ For standalone operation, a Qt application object must be created to support the windows. """
        app = QApplication(sys.argv)
        super().__init__(**kwargs)
        self.new_window(MainWindow())
        app.exec_()

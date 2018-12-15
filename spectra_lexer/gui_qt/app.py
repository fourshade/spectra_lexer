import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.display.cascaded_text import CascadedTextFormatter
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
                "app_query_and_display":      self.query_and_display,
                "app_query_and_display_best": self.query_and_display_best}

    def engine_subcomponents(self) -> tuple:
        """ Default GUI support components. """
        return (*super().engine_subcomponents(), CascadedTextFormatter())

    def dialog_load_translations(self, *args) -> None:
        """ Present a dialog for the user to select one or more steno dictionary files.
            Attempt to load it if not empty. """
        file_formats = self.engine_call("file_get_decodable_exts")
        fname = self.engine_call("gui_dialog_load_dict", file_formats)
        if fname:
            self.load_translations_from((fname,), src_string="file dialog")

    def query_and_display(self, strokes, text) -> None:
        """ Make a lexer query and display the results. """
        result = self.engine_call("lexer_query", strokes, text)
        self.engine_call("display_rule", result)

    def query_and_display_best(self, strokes_list, text) -> str:
        """ Make a lexer query for several strokes and display the results.
            Return the best-performing keys (parsed back into RTFCRE) to the caller. """
        result = self.engine_call("lexer_query_all", strokes_list, text)
        self.engine_call("display_rule", result)
        return result.keys.inv_parse()


class GUIQtMainApplication(GUIQtBaseApplication):
    """ Top-level class for operation of the Spectra program by itself with the standard GUI. """

    def __init__(self, **kwargs) -> None:
        """ For standalone operation, a Qt application object must be created to support the windows. """
        app = QApplication(sys.argv)
        super().__init__(**kwargs)
        self.new_window(MainWindow())
        app.exec_()

from PyQt5.QtWidgets import QCheckBox, QLabel, QLineEdit, QMainWindow, QMenuBar

from .main_window import MainWindow
from .search_list_widget import SearchListWidget
from .steno_board_widget import StenoBoardWidget
from .text_graph_widget import TextGraphWidget
from .text_title_widget import TextTitleWidget
from spectra_lexer.core import COREApp, Command, Component, Resource, Signal
from spectra_lexer.steno import LXAnalyzer
from spectra_lexer.system import SYSControl
from spectra_lexer.types import delegate_to


class GUI:
    """ Mapping of Python widget resource classes to internal Qt Designer names. """

    class Window:
        """ Main GUI window. All GUI activity (including dialogs) is coupled to this window. """
        window: QMainWindow = Resource()

    class Menu:
        KEY = "m_menu"
        w_menu: QMenuBar = Resource()

    class DisplayBoard:
        KEY = "w_display_board"
        w_board: StenoBoardWidget = Resource()

    class DisplayDescription:
        KEY = "w_display_desc"
        w_desc: QLabel = Resource()

    class DisplayTitle:
        KEY = "w_display_title"
        w_title: TextTitleWidget = Resource()

    class DisplayGraph:
        KEY = "w_display_text"
        w_text: TextGraphWidget = Resource()

    class SearchInput:
        KEY = "w_search_input"
        w_input: QLineEdit = Resource()

    class SearchMatchList:
        KEY = "w_search_matches"
        w_matches: SearchListWidget = Resource()

    class SearchMappingList:
        KEY = "w_search_mappings"
        w_mappings: SearchListWidget = Resource()

    class SearchToggleStrokes:
        KEY = "w_search_type"
        w_strokes: QCheckBox = Resource()

    class SearchToggleRegex:
        KEY = "w_search_regex"
        w_regex: QCheckBox = Resource()


    @Command
    def show(self) -> None:
        """ For a plugin window, this is called by its host application to re-open it. """
        raise NotImplementedError

    @Command
    def close(self) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        raise NotImplementedError

    class Enabled:
        @Signal
        def on_window_enabled(self, enabled:bool) -> None:
            """ Enable/disable all input widgets. """
            raise NotImplementedError


class QtWindow(Component, GUI,
               COREApp.Start, LXAnalyzer.Ready, LXAnalyzer.Start, LXAnalyzer.Finish):
    """ GUI Qt operations class for the main window. """

    _window: MainWindow  # Main GUI window. All GUI activity (including dialogs) is coupled to this window.

    def __init__(self):
        self._window = MainWindow()

    def on_app_start(self) -> None:
        """ Set the GUI controls off until everything is mostly done loading. """
        self._send_widgets()
        self.engine_call(SYSControl.status, "Loading...")
        self._set_enabled(False)
        self.show()

    def _send_widgets(self):
        """ Get all widgets created by the generated Python code for the window and send them to GUI components. """
        window = self._window
        self.engine_call(self.Window, window)
        for v in vars(GUI).values():
            if type(v) is type:
                try:
                    self.engine_call(v, getattr(window, v.KEY))
                except AttributeError:
                    pass

    def _set_enabled(self, enabled:bool) -> None:
        self.engine_call(self.Enabled, enabled)

    show = delegate_to("_window")
    close = delegate_to("_window")

    def on_analyzer_ready(self) -> None:
        """ When the analyzer has all its resources loaded, the system as a whole is ready to use. """
        self._set_enabled(True)
        self.engine_call(SYSControl.status, "Loading complete.")

    def on_analyzer_start(self) -> None:
        """ It is not thread-safe for the GUI to access certain objects while the analyzer is running. Disable it. """
        self._set_enabled(False)

    def on_analyzer_finish(self) -> None:
        """ Re-enable the GUI when the analyzer is done. """
        self._set_enabled(True)

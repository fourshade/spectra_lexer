import pkgutil
from typing import Callable, List

from PyQt5.QtWidgets import QMainWindow

from .display import DisplayController
from .main_window_ui import Ui_MainWindow
from .menu import MenuController
from .search import SearchController
from .tools import ConfigTool, ConsoleTool, IndexSizeTool, ObjectTreeTool
from .window import WindowController


INDEX_STARTUP_MESSAGE = """<p>
In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
Would you like to create one now? You will not be asked again.
</p><p>
(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).
</p>"""


class QtGUI:

    def __init__(self, window:WindowController, menu:MenuController,
                 search:SearchController, display:DisplayController) -> None:
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        self.show = window.show
        self.close = window.close
        self.menu_add = menu.add
        self.set_status = display.set_status
        self.show_traceback = display.show_traceback

    def connect(self, action_fn:Callable[..., None]) -> None:
        """ Connect all GUI input signals to the action function. """
        self._search.connect(action_fn)
        self._display.connect(action_fn)

    def get_options(self) -> dict:
        return {**self._search.get_options(),
                **self._display.get_options()}

    def update(self, *args, **kwargs) -> None:
        self._search.update(*args, **kwargs)
        self._display.update(*args, **kwargs)

    def enable(self, msg:str=None) -> None:
        """ Enable all widgets when GUI-blocking operations are done. """
        self._set_enabled(True)
        if msg is not None:
            self.set_status(msg)

    def disable(self, msg:str=None) -> None:
        """ Disable all widgets when GUI-blocking operations start. """
        self._set_enabled(False)
        if msg is not None:
            self.set_status(msg)

    def _set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are running. """
        self._menu.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._display.set_enabled(enabled)

    def select_translations_files(self) -> List[str]:
        """ Present a modal dialog for the user to select translation files. """
        return self._window.open_files("Load Translations", "json")

    def select_index_file(self) -> str:
        """ Present a modal dialog for the user to select an index file. """
        return self._window.open_file("Load Index", "json")

    def confirm_startup_index(self) -> bool:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        return self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE)

    def open_index_tool(self) -> IndexSizeTool:
        """ Return a dialog tool with an index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog("Choose Index Size", 360, 320)
        if dialog is not None:
            return IndexSizeTool(dialog)

    def open_config_tool(self) -> ConfigTool:
        """ Return a GUI configuration manager dialog tool. """
        dialog = self._window.open_dialog("Spectra Configuration", 250, 300)
        if dialog is not None:
            return ConfigTool(dialog)

    def open_debug_console(self) -> ConsoleTool:
        """ Return a dialog tool for the debug console. """
        dialog = self._window.open_dialog("Python Console", 680, 480)
        if dialog is not None:
            return ConsoleTool(dialog)

    def open_debug_tree(self) -> ObjectTreeTool:
        """ Return a dialog tool for the debug tree. """
        dialog = self._window.open_dialog("Python Object Tree View", 600, 450)
        if dialog is not None:
            return ObjectTreeTool(dialog)


class QtGUIFactory:

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for window icon.

    def __init__(self, w_window:QMainWindow=None) -> None:
        self._w_window = w_window or QMainWindow()

    def build(self) -> QtGUI:
        w_window = self._w_window
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window = WindowController(w_window)
        window.load_icon(icon_data)
        menu = MenuController(ui.w_menubar)
        search = SearchController.from_widgets(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController.from_widgets(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption)
        return QtGUI(window, menu, search, display)

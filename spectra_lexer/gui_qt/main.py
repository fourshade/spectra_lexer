""" Main entry point for Spectra's interactive GUI application. """

import pkgutil
import sys
from functools import partial
from traceback import format_exception
from typing import Any, Callable, Type

from PyQt5.QtWidgets import QApplication, QMainWindow

from .system import QtExceptionTrap, QtAsyncDispatcher
from .tools import QtDialogTools
from .window import DisplayController, SearchController, Ui_MainWindow, WindowController
from spectra_lexer.app import StenoApplication
from spectra_lexer.base import StenoMain
from spectra_lexer.log import StreamLogger


class QtGUI:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: Exception = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, logger:StreamLogger, exc_trap: QtExceptionTrap, async_dsp: QtAsyncDispatcher,
                 window:WindowController, search:SearchController, display:DisplayController,
                 tools:QtDialogTools, **kwargs) -> None:
        self._logger = logger
        self._exc_trap = exc_trap
        self._async_dsp = async_dsp
        self._window = window
        self._search = search
        self._display = display
        # Dict of all possible GUI methods to call when a particular part of the state changes.
        self._methods = {"input_text":       self._search.set_input,
                         "matches":          self._search.set_matches,
                         "match_selected":   self._search.select_match,
                         "mappings":         self._search.set_mappings,
                         "mapping_selected": self._search.select_mapping,
                         "translation":      self._display.set_translation,
                         "graph_text":       self._display.set_graph_text,
                         "board_caption":    self._display.set_caption,
                         "board_xml_data":   self._display.set_board_xml,
                         "link_ref":         self._display.set_link}
        # List of all GUI input events that can result in a call to a steno engine action.
        self._events = [(self._search.sig_strokes_mode, "Search", "mode_strokes"),
                        (self._search.sig_regex_mode, "Search", "mode_regex"),
                        (self._search.sig_edit_input, "Search", "input_text"),
                        (self._search.sig_select_match, "Lookup", "match_selected"),
                        (self._search.sig_select_mapping, "Select", "mapping_selected"),
                        (self._display.sig_edit_translation, "Query", "translation"),
                        (self._display.sig_over_graph, "GraphOver", "graph_node_ref"),
                        (self._display.sig_click_graph, "GraphClick", "graph_node_ref"),
                        (self._display.sig_activate_link, "SearchExamples", None),
                        (self._display.sig_board_ratio, "GraphOver", "board_aspect_ratio")]
        self._tools = tools
        self._app = None
        self._state_vars = {}  # Contains a complete representation of the current state of the GUI.

    def start(self, app_builder:Callable[[], StenoApplication]) -> None:
        """ Connect all dialog menu items through the exception trap. """
        exc_trap = self._exc_trap
        exc_trap.connect(self._handle_exception)
        def menu_add(menu_callback:Callable, *args, **kwargs) -> None:
            self._window.menu_add(exc_trap.wrap(menu_callback), *args, **kwargs)
        menu_add(self._open_translations, "File", "Load Translations...")
        menu_add(self._open_index, "File", "Load Index...")
        menu_add(self._window.close, "File", "Close", after_sep=True)
        menu_add(self._config_editor, "Tools", "Edit Configuration...")
        menu_add(self._custom_index, "Tools", "Make Index...")
        menu_add(self._debug_console, "Debug", "Open Console...")
        menu_add(self._debug_tree, "Debug", "View Object Tree...")
        # Build the app object asynchronously on a new thread to avoid blocking the GUI.
        self._display.set_status("Loading...")
        self._run_async(app_builder, callback=self._connect, msg_done="Loading complete.")
        self._window.show()

    def _connect(self, app:StenoApplication) -> None:
        """ Once the app object is loaded, it is safe to connect GUI extensions.
            Connect all input signals to the function with their corresponding action and/or state attribute. """
        self._app = app
        update_action = self._exc_trap.wrap(self._update_action)
        for signal, action, attr in self._events:
            fn = partial(update_action, action, attr)
            signal.connect(fn)
        # Initialize the board size after all connections are made.
        w, h = self._display.get_board_size()
        update_action("GraphOver", "board_aspect_ratio", w / h)
        self._subcls_tasks()
        # If there is no index file on first start, send up a dialog.
        if app.is_first_run:
            self._default_index()

    def _subcls_tasks(self) -> None:
        """ Perform subclass-specific setup. """
        pass

    def _query(self, strokes:str, word:str) -> None:
        """ Run a lexer query on actual user strokes from a steno machine. """
        self._update(translation=[strokes, word])
        state = {"match_all_keys": False, **self._state_vars}
        self._action(state, "Query")

    def _update_action(self, action:str, attr:str=None, value:Any=None) -> None:
        """ Update the state with a value from a GUI event, then run the action. """
        state = self._state_vars
        if attr is not None:
            state[attr] = value
        self._action(state, action)

    def _update(self, **state_vars) -> None:
        """ For every variable given, update our state dict and call the corresponding GUI method if one exists. """
        self._state_vars.update(state_vars)
        for k in self._methods:
            if k in state_vars:
                self._methods[k](state_vars[k])

    def _action(self, state:dict, action:str) -> None:
        """ Send an action command with the given state. """
        changed = self._app.process_action(state, action)
        # After any action, run through the changes and update the state and widgets with any relevant ones.
        self._update(**changed)

    def _open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._tools.open_translations_files()
        if filenames:
            self._run_async(self._app.load_translations, *filenames, msg_done="Loaded translations from file dialog.")

    def _open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._tools.open_index_file()
        if filename:
            self._run_async(self._app.load_index, filename, msg_done="Loaded index from file dialog.")

    def _config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        self._tools.config(self._update_config, self._app.get_config_info())

    def _update_config(self, options:dict) -> None:
        self._run_async(self._app.set_config, options, msg_done="Configuration saved.")

    def _default_index(self) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        if self._tools.confirm_startup_index():
            self._make_index()

    def _custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._tools.custom_index(self._make_index, self._app.get_index_info())

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self._display.set_status("Making new index...")
        self._run_async(self._app.make_index, size, msg_done="Successfully created index!")

    def _debug_console(self) -> None:
        """ Create and show the debug console dialog. """
        self._tools.console(vars(self).copy())

    def _debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        self._tools.objtree(vars(self).copy())

    def _run_async(self, func:Callable, *args, callback:Callable=None, msg_done:str=None) -> None:
        """ Disable the window controls in order to start a blocking async task.
            Make a callback that will re-enable the controls and optionally show <msg_done> when the task is done.
            This may wrap another <callback> that will be called with the original arguments afterward. """
        self._set_enabled(False)
        def on_task_finish(*args, **kwargs) -> None:
            self._set_enabled(True)
            if msg_done is not None:
                self._display.set_status(msg_done)
            if callback is not None:
                callback(*args, **kwargs)
        self._async_dsp.dispatch(func, *args, callback=on_task_finish)

    def _handle_exception(self, exc:Exception, max_frames=20) -> None:
        """ Format, log, and display a stack trace for any thrown exception.
            Store the exception and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=max_frames))
        self._logger.log('EXCEPTION\n' + tb_text)
        self._display.show_traceback(tb_text)
        self._set_enabled(True)

    def _set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done. """
        self._window.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._display.set_enabled(enabled)


class QtMain(StenoMain):
    """ Main entry point and factory for the Qt GUI. """

    ICON_PATH = __package__, 'icon.svg'  # Package and relative file path for window icon.

    def build_gui(self, gui_cls:Type[QtGUI], **kwargs) -> WindowController:
        """ Build all components necessary to operate the GUI. """
        logger = self.build_logger()
        exc_trap = QtExceptionTrap()
        dsp = QtAsyncDispatcher(exc_trap)
        w_window = QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window = WindowController(w_window, ui.w_menubar)
        window.load_icon(icon_data)
        search = SearchController(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption)
        dialogs = QtDialogTools(w_window)
        gui = gui_cls(logger, exc_trap, dsp, window, search, display, dialogs, **kwargs)
        gui.start(self.build_app)
        return window

    def main(self) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = self.build_gui(QtGUI)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()

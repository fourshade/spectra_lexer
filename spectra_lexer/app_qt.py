""" Main module for the interactive Qt GUI application. """

import pkgutil
import sys
from typing import Callable, Iterable

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.base import Spectra
from spectra_lexer.engine import StenoEngine
from spectra_lexer.gui import GUILayer, GUIOptions, GUIOutput
from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.display import DisplayController, DisplayPageData, DisplayPageDict
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchController
from spectra_lexer.qt.system import QtAsyncDispatcher, QtExceptionHook
from spectra_lexer.qt.window import WindowController
from spectra_lexer.resource.translations import RTFCREDict
from spectra_lexer.util.cmdline import CmdlineOptions
from spectra_lexer.util.config import ConfigFile
from spectra_lexer.util.exception import ExceptionManager


class QtGUIConfig:
    """ Keeps track of configuration options in a dict corresponding to one section of a CFG file. """

    def __init__(self, file:ConfigFile, sect="app_qt") -> None:
        self._file = file   # CFG file I/O wrapper.
        self._sect = sect   # Name of the CFG file section.
        self._options = {}  # Stores the current values of all loaded options.

    def to_dict(self) -> dict:
        """ Return a copy of all options in a dict. """
        return self._options.copy()

    def read(self) -> bool:
        """ Try to read config options from the CFG file. Return True if successful. """
        try:
            cfg = self._file.read()
            self._options = cfg.get(self._sect) or {}
            return True
        except (KeyError, OSError):
            return False

    def update(self, options:dict) -> None:
        """ Update the config dict with <options> and save them back to the original CFG file. """
        self._options.update(options)
        cfg = {self._sect: self._options}
        self._file.write(cfg)


class QtGUIApplication:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, engine:StenoEngine, gui:GUILayer, config:QtGUIConfig, async_dsp:QtAsyncDispatcher,
                 window:WindowController, menu:MenuController, search:SearchController, display:DisplayController,
                 translations_paths:Iterable[str], examples_path:str) -> None:
        self._engine = engine
        self._gui = gui
        self._config = config
        self._async_dsp = async_dsp
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        self._translations_paths = translations_paths  # Initial translations file paths.
        self._examples_path = examples_path            # Initial examples index file path.

    def _get_options(self, ext_opts:dict) -> GUIOptions:
        """ Add all values that may be needed by the steno engine as options in precedence order. """
        cfg_opts = self._config.to_dict()
        gui_opts = dict(search_mode_strokes=self._search.get_mode_strokes(),
                        search_mode_regex=self._search.get_mode_regex(),
                        board_aspect_ratio=self._display.get_board_ratio(),
                        board_show_compound=self._display.get_board_compound(),
                        board_show_letters=self._display.get_board_letters())
        return GUIOptions(cfg_opts, gui_opts, ext_opts)

    def on_search(self, pattern:str, pages:int, **options) -> None:
        """ Run a translation search and update the GUI with any results. """
        opts = self._get_options(options)
        out = self._gui.search(pattern, pages, opts=opts)
        self._update_gui(out)

    def on_query(self, *args, **options) -> None:
        """ Run a lexer query and update the GUI with any results. """
        opts = self._get_options(options)
        out = self._gui.query(*args, opts=opts)
        self._update_gui(out)

    def on_search_examples(self, link_ref:str, **options) -> None:
        """ Run an example search and update the GUI with any results. """
        opts = self._get_options(options)
        out = self._gui.search_examples(link_ref, opts=opts)
        self._update_gui(out)

    def _update_gui(self, out:GUIOutput) -> None:
        """ Update each GUI component with anything it uses from <out>. """
        search_input = out.search_input
        if out.search_input is not None:
            self._search.update_input(search_input)
        results = out.search_results
        if results is not None:
            self._search.update_results(results.matches, can_expand=not results.is_complete)
        display_data = out.display_data
        if display_data is not None:
            self._update_gui_translation(display_data.keys, display_data.letters)
            default_item = (DisplayPageDict.DEFAULT_KEY, display_data.default_page)
            input_items = [default_item, *display_data.pages_by_ref.items()]
            output_dict = DisplayPageDict()
            for ref, page in input_items:
                graphs = [page.graph, page.intense_graph]
                board_xml = page.board.encode('utf-8')
                output_dict[ref] = DisplayPageData(graphs, page.caption, board_xml, page.rule_id)
            self._display.set_pages(output_dict)

    def _update_gui_translation(self, keys:str, letters:str) -> None:
        self._search.select_translation(keys, letters)
        self._display.set_translation(keys, letters)

    def run_async(self, func:Callable, *args, callback:Callable=None, msg_start:str=None, msg_done:str=None) -> None:
        """ Start a blocking async task. If <msg_start> is not None, show it and disable the window controls.
            Make a callback that will re-enable the controls and show <msg_done> when the task is done.
            GUI events may misbehave unless explicitly processed before the async thread takes the GIL. """
        q_app = QApplication.instance()
        def on_task_start() -> None:
            if msg_start is not None:
                self.set_enabled(False)
                self.set_status(msg_start)
        def on_task_finish(val) -> None:
            if msg_start is not None:
                self.set_enabled(True)
            if msg_done is not None:
                self.set_status(msg_done)
            if callback is not None:
                callback(val)
        q_app.processEvents()
        self._async_dsp.dispatch(func, *args, on_start=on_task_start, on_finish=on_task_finish)

    def load_engine(self) -> None:
        """ Load initial data asynchronously on a new thread to avoid blocking the GUI. """
        self.run_async(self._load_engine_async, callback=self._on_engine_loaded,
                       msg_start="Loading...", msg_done="Loading complete.")

    def _load_engine_async(self) -> bool:
        """ Load the engine translations and ignore examples index I/O errors since it may be missing.
            If the config file is missing, create it with default values and return True. """
        self._engine.load_translations(*self._translations_paths)
        try:
            self._engine.load_examples(self._examples_path)
        except OSError:
            pass
        is_first_run = not self._config.read()
        if is_first_run:
            options = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self._config.update(options)
        return is_first_run

    def _on_engine_loaded(self, is_first_run:bool) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        self._search.call_on_search(self.on_search)
        self._search.call_on_query(self.on_query)
        self._display.call_on_query(self.on_query)
        self._display.call_on_example_search(self.on_search_examples)
        if is_first_run:
            self.confirm_startup_index()

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._window.open_files("Load Translations", ".", "json")
        if filenames:
            self.run_async(self._engine.load_translations, *filenames,
                           msg_start="Loading files...", msg_done="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._window.open_file("Load Index", ".", "json")
        if filename:
            self.run_async(self._engine.load_examples, filename,
                           msg_start="Loading file...", msg_done="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._window.open_dialog(ConfigDialog)
        if dialog is not None:
            opts = self._get_options({})
            for key, name, description in GUIOptions.CFG_OPTIONS:
                value = getattr(opts, key)
                dialog.add_option(key, value, "General", name, description)
                dialog.call_on_options_accept(self._update_config)
            dialog.show()

    def _update_config(self, options:dict) -> None:
        self.run_async(self._config.update, options, msg_done="Configuration saved.")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index(RTFCREDict.FSIZE_MEDIUM)

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog(IndexSizeDialog)
        if dialog is not None:
            dialog.setup(RTFCREDict.FILTER_SIZES)
            dialog.call_on_size_accept(self._make_index)
            dialog.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.run_async(self._engine.compile_examples, size, self._examples_path,
                       msg_start="Making new index...", msg_done="Successfully created index!")

    def debug_console(self) -> None:
        """ Create and show an interpreter console dialog. """
        dialog = self._window.open_dialog(ConsoleDialog)
        if dialog is not None:
            namespace = {k: getattr(self, k) for k in dir(self) if not k.startswith('__')}
            dialog.start_console(namespace)
            dialog.show()

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog with this app's vars. """
        dialog = self._window.open_dialog(NamespaceTreeDialog)
        if dialog is not None:
            dialog.set_namespace(vars(self), root_package=__package__)
            dialog.show()

    def show(self) -> None:
        self._window.show()

    def close(self) -> None:
        self._window.close()

    def set_status(self, status:str) -> None:
        self._display.set_status(status)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are running. """
        self._menu.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._display.set_enabled(enabled)

    def on_exception(self, exc:BaseException) -> None:
        """ Store unhandled exceptions and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        self.set_enabled(True)


class QtAppFactory:
    """ Builds the interactive GUI application. """

    ICON_PATH = __package__, 'qt/icon.svg'  # Package and relative file path for window icon.

    def __init__(self, spc:Spectra=None) -> None:
        """ Some objects must be saved on attributes or else Qt will disconnect the signals upon scope exit. """
        self._spc = spc or Spectra()
        self._exc_man = ExceptionManager()
        self._exc_hook = QtExceptionHook(chain_hooks=False)
        self._exc_man.add_logger(self.log_exception)
        self._exc_hook.connect(self._exc_man.on_exception)

    def log_exception(self, s:str) -> None:
        """ Add a line to differentiate exception log messages from normal ones. """
        self._spc.log('EXCEPTION\n' + s)

    def build_app(self) -> QtGUIApplication:
        """ Build the app with all components necessary to operate the GUI. """
        w_window = QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        window = WindowController(w_window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window.set_icon(icon_data)
        menu = MenuController(ui.w_menubar)
        search = SearchController.from_widgets(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController.from_widgets(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption, ui.w_slider)
        self._exc_man.add_logger(display.show_traceback)
        translations_paths = self._spc.translations_paths()
        index_path = self._spc.index_path()
        engine = self._spc.build_engine()
        gui = GUILayer(engine)
        cfg_path = self._spc.config_path()
        config_file = ConfigFile(cfg_path)
        config = QtGUIConfig(config_file)
        async_dsp = QtAsyncDispatcher()
        app = QtGUIApplication(engine, gui, config, async_dsp,
                               window, menu, search, display, translations_paths, index_path)
        self._exc_man.add_handler(app.on_exception)
        menu.add(app.open_translations, "File", "Load Translations...")
        menu.add(app.open_index, "File", "Load Index...")
        menu.add(app.close, "File", "Close", after_sep=True)
        menu.add(app.config_editor, "Tools", "Edit Configuration...")
        menu.add(app.custom_index, "Tools", "Make Index...")
        menu.add(app.debug_console, "Debug", "Open Console...")
        menu.add(app.debug_tree, "Debug", "View Object Tree...")
        app.set_enabled(False)
        app.set_status("Loading...")
        app.show()
        return app


def main() -> int:
    """ In standalone mode, we must create a QApplication before building any of the GUI. """
    opts = CmdlineOptions("Run Spectra as a standalone GUI application.")
    spectra = Spectra(opts)
    q_app = QApplication(sys.argv)
    factory = QtAppFactory(spectra)
    app = factory.build_app()
    app.load_engine()
    # After everything is loaded, start a GUI event loop and run it indefinitely.
    return q_app.exec_()


if __name__ == '__main__':
    sys.exit(main())

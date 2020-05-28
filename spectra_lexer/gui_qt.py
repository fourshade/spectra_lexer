import pkgutil
from typing import Callable

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.analysis import TranslationFilter
from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.engine import StenoEngine
from spectra_lexer.gui import GUILayer, GUIOptions, GUIOutput
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt import WINDOW_ICON_PATH
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.display import DisplayController, DisplayPageDict, DisplayPageData
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchController
from spectra_lexer.qt.system import QtAsyncDispatcher, QtExceptionHook
from spectra_lexer.qt.window import WindowController
from spectra_lexer.util.config import SimpleConfigDict
from spectra_lexer.util.exception import ExceptionManager


class QtGUIApplication:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, engine:StenoEngine, gui:GUILayer, config:SimpleConfigDict, async_dsp:QtAsyncDispatcher,
                 window:WindowController, menu:MenuController, search:SearchController, display:DisplayController,
                 examples_path:str, sys_refs:list) -> None:
        self._engine = engine
        self._gui = gui
        self._config = config
        self._async_dsp = async_dsp
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        self._examples_path = examples_path  # User examples index file path.
        self._sys_refs = sys_refs            # List of Qt system objects that must be retained until close.

    def _get_options(self) -> GUIOptions:
        """ Add all values that may be needed by the steno engine as options in precedence order. """
        opts = GUIOptions(self._config)
        opts.search_mode_strokes = self._search.get_mode_strokes()
        opts.search_mode_regex = self._search.get_mode_regex()
        opts.board_aspect_ratio = self._display.get_board_ratio()
        opts.board_show_compound = self._display.get_board_compound()
        opts.board_show_letters = self._display.get_board_letters()
        return opts

    def _update_gui_translation(self, keys:str, letters:str) -> None:
        self._search.select_translation(keys, letters)
        self._display.set_translation(keys, letters)

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

    def on_search(self, pattern:str, pages:int) -> None:
        """ Run a translation search and update the GUI with any results. """
        opts = self._get_options()
        self._gui.set_options(opts)
        out = self._gui.search(pattern, pages)
        self._update_gui(out)

    def on_query(self, *args, strict:bool=None) -> None:
        """ Run a lexer query and update the GUI with any results. """
        opts = self._get_options()
        if strict is not None:
            opts.lexer_strict_mode = strict
        self._gui.set_options(opts)
        out = self._gui.query(*args)
        self._update_gui(out)

    def on_search_examples(self, link_ref:str) -> None:
        """ Run an example search and update the GUI with any results. """
        opts = self._get_options()
        self._gui.set_options(opts)
        out = self._gui.search_examples(link_ref)
        self._update_gui(out)

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

    def _update_config(self, options:dict) -> None:
        self._config.update(options)
        self._config.write()

    def _load_user_files(self) -> bool:
        """ Load the examples index and config files. Ignore I/O errors since either may be missing.
            If the config file is missing, create it with default values and return True. """
        try:
            self._engine.load_examples(self._examples_path)
        except OSError:
            pass
        is_first_run = not self._config.read()
        if is_first_run:
            options = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self._update_config(options)
        return is_first_run

    def _on_ready(self, is_first_run:bool) -> None:
        """ When all resources are ready, connect the GUI callbacks.
            Present an index generation dialog if this is the first time the program has been run. """
        self._search.call_on_search(self.on_search)
        self._search.call_on_query(self.on_query)
        self._display.call_on_query(self.on_query)
        self._display.call_on_example_search(self.on_search_examples)
        if is_first_run:
            self.confirm_startup_index()

    def load_user_files(self) -> None:
        """ Load initial data asynchronously on a new thread to avoid blocking the GUI. """
        self.run_async(self._load_user_files, callback=self._on_ready,
                       msg_start="Loading...", msg_done="Loading complete.")

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

    def _config_edited(self, options:dict) -> None:
        self.run_async(self._update_config, options, msg_done="Configuration saved.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._window.open_dialog(ConfigDialog)
        if dialog is not None:
            opts = self._get_options()
            for key, name, description in GUIOptions.CFG_OPTIONS:
                value = getattr(opts, key)
                dialog.add_option(key, value, "General", name, description)
                dialog.call_on_options_accept(self._config_edited)
            dialog.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.run_async(self._engine.compile_examples, size, self._examples_path,
                       msg_start="Making new index...", msg_done="Successfully created index!")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index(TranslationFilter.SIZE_MEDIUM)

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog(IndexSizeDialog)
        if dialog is not None:
            dialog.setup(TranslationFilter.SIZES)
            dialog.call_on_size_accept(self._make_index)
            dialog.show()

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

    def has_focus(self) -> bool:
        return self._window.has_focus()

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

    @classmethod
    def build(cls, engine:StenoEngine, logger:Callable[[str], None],
              examples_path:str, cfg_path:str) -> "QtGUIApplication":
        """ Build the interactive Qt GUI application with all necessary components. """
        exc_man = ExceptionManager()
        exc_man.add_logger(logger)
        exc_hook = QtExceptionHook(chain_hooks=False)
        exc_hook.connect(exc_man.on_exception)
        gui = GUILayer(engine)
        config = SimpleConfigDict(cfg_path, "app_qt")
        async_dsp = QtAsyncDispatcher()
        w_window = QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        window = WindowController(w_window)
        icon_data = pkgutil.get_data(*WINDOW_ICON_PATH)
        window.set_icon(icon_data)
        menu = MenuController(ui.w_menubar)
        search = SearchController.from_widgets(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController.from_widgets(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption, ui.w_slider)
        # Some object references must be saved in an attribute or else Qt will disconnect the signals upon scope exit.
        sys_refs = [exc_man, exc_hook]
        self = cls(engine, gui, config, async_dsp, window, menu, search, display, examples_path, sys_refs)
        exc_man.add_logger(display.show_traceback)
        exc_man.add_handler(self.on_exception)
        menu.add(self.open_translations, "File", "Load Translations...")
        menu.add(self.open_index, "File", "Load Index...")
        menu.add(self.close, "File", "Close", after_sep=True)
        menu.add(self.config_editor, "Tools", "Edit Configuration...")
        menu.add(self.custom_index, "Tools", "Make Index...")
        menu.add(self.debug_console, "Debug", "Open Console...")
        menu.add(self.debug_tree, "Debug", "View Object Tree...")
        self.set_enabled(False)
        self.set_status("Loading...")
        self.show()
        return self

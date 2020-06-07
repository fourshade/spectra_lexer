import pkgutil
from typing import Callable, Sequence

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.analysis import TranslationFilter
from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.gui_engine import GUIEngine, GUIOptions, GUIOutput
from spectra_lexer.gui_ext import GUIExtension
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt import WINDOW_ICON_PATH
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.display import DisplayBoard, DisplayController, DisplayGraph, DisplayPageData, DisplayTitle
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchController
from spectra_lexer.qt.system import QtTaskExecutor, QtExceptionHook
from spectra_lexer.qt.window import WindowController
from spectra_lexer.util.exception import ExceptionManager


class QtGUIApplication:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, engine:GUIEngine, ext:GUIExtension, tasks:QtTaskExecutor, window:WindowController,
                 menu:MenuController, search:SearchController, display:DisplayController) -> None:
        self._engine = engine
        self._ext = ext
        self._tasks = tasks
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display

    def _get_options(self) -> GUIOptions:
        """ Add all values that may be needed by the steno engine as options in precedence order. """
        opts = GUIOptions(self._ext.get_config())
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
            d = display_data.pages_by_ref
            in_pages = [*d.values(), display_data.default_page]
            out_pages = [DisplayPageData((p.graph, p.intense_graph), p.caption, p.board, p.rule_id) for p in in_pages]
            default = out_pages.pop()
            self._display.set_pages(dict(zip(d, out_pages)), default)

    def gui_search(self, pattern:str, pages:int) -> None:
        """ Run a translation search and update the GUI with any results. """
        opts = self._get_options()
        self._engine.set_options(opts)
        out = self._engine.search(pattern, pages)
        self._update_gui(out)

    def gui_query(self, keys_or_seq:Sequence[str], letters:str, strict:bool=None) -> None:
        """ Run a lexer query and update the GUI with any results. """
        opts = self._get_options()
        if strict is not None:
            opts.lexer_strict_mode = strict
        self._engine.set_options(opts)
        out = self._engine.query(keys_or_seq, letters)
        self._update_gui(out)

    def gui_search_examples(self, link_ref:str) -> None:
        """ Run an example search and update the GUI with any results. """
        opts = self._get_options()
        self._engine.set_options(opts)
        out = self._engine.search_examples(link_ref)
        self._update_gui(out)

    def has_focus(self) -> bool:
        return self._window.has_focus()

    def show(self) -> None:
        self._window.show()

    def close(self) -> None:
        self._window.close()

    def set_status(self, status:str) -> None:
        self._display.set_status(status)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets. """
        self._menu.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._display.set_enabled(enabled)

    def async_run(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the worker thread. """
        self._tasks.on_worker(func, *args)

    def async_queue(self, func:Callable, *args) -> None:
        """ Queue a function to execute on the GUI thread. Only useful for sequencing. """
        self._tasks.on_main(func, *args)

    def async_start(self, msg_start:str) -> None:
        """ Disable the window controls and show <msg_start> first before running a blocking task on another thread.
            GUI events may misbehave unless explicitly processed before the async thread takes the GIL. """
        q_app = QApplication.instance()
        q_app.processEvents()
        self.async_queue(self.set_enabled, False)
        self.async_queue(self.set_status, msg_start)

    def async_finish(self, msg_finish:str) -> None:
        """ Queue callbacks that will re-enable the controls and show <msg_finish> when all worker tasks are done. """
        self.async_queue(self.set_enabled, True)
        self.async_queue(self.set_status, msg_finish)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._window.open_files("Load Translations", "json")
        if filenames:
            self.async_start("Loading files...")
            self.async_run(self._ext.load_translations, *filenames)
            self.async_finish("Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._window.open_file("Load Index", "json")
        if filename:
            self.async_start("Loading file...")
            self.async_run(self._ext.load_examples, filename)
            self.async_finish("Loaded index from file dialog.")

    def _config_edited(self, options:dict) -> None:
        self._ext.update_config(options)
        self.set_status("Configuration saved.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._window.open_dialog(ConfigDialog)
        if dialog is not None:
            options = self._ext.get_config()
            for key, name, description in GUIOptions.CFG_OPTIONS:
                value = getattr(options, key)
                dialog.add_option(key, value, "General", name, description)
                dialog.call_on_options_accept(self._config_edited)
            dialog.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.async_start("Making new index...")
        self.async_run(self._ext.compile_examples, size)
        self.async_finish("Successfully created index!")

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

    def _on_ready(self) -> None:
        """ When all major resources are ready, load the config and connect the GUI callbacks.
            If the config settings are blank, this is the first time the program has been run.
            Add the default config values and present an index generation dialog in this case. """
        self._search.connect_signals(self.gui_search, self.gui_query)
        self._display.connect_signals(self.gui_search_examples, self.gui_query)
        if not self._ext.get_config():
            defaults = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self._ext.update_config(defaults)
            self.confirm_startup_index()

    def start(self, *funcs:Callable[[], None]) -> None:
        """ Load initial data from <funcs> asynchronously on a new thread to avoid blocking the GUI. """
        self._tasks.start()
        self.async_start("Loading...")
        for f in funcs:
            self.async_run(f)
        self.async_finish("Loading complete.")
        self.async_queue(self._on_ready)

    def on_exception(self, exc:BaseException) -> None:
        """ Store unhandled exceptions and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        self.set_enabled(True)


def build_app(engine:GUIEngine, ext:GUIExtension, logger:Callable[[str], None]) -> QtGUIApplication:
    """ Build the interactive Qt GUI application with all necessary components. """
    exc_man = ExceptionManager()
    exc_man.add_logger(logger)
    exc_hook = QtExceptionHook(chain_hooks=False)
    exc_hook.connect(exc_man.on_exception)
    tasks = QtTaskExecutor()
    w_window = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(w_window)
    window = WindowController(w_window)
    icon_data = pkgutil.get_data(*WINDOW_ICON_PATH)
    window.set_icon(icon_data)
    menu = MenuController(ui.w_menubar)
    search = SearchController(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
    d_title = DisplayTitle(ui.w_title)
    d_graph = DisplayGraph(ui.w_graph)
    d_board = DisplayBoard(ui.w_board, ui.w_link_save)
    display = DisplayController(d_title, d_graph, d_board, ui.w_caption, ui.w_slider, ui.w_link_examples)
    display.set_status("Loading...")
    app = QtGUIApplication(engine, ext, tasks, window, menu, search, display)
    exc_man.add_logger(display.show_traceback)
    exc_man.add_handler(app.on_exception)
    menu.add(app.open_translations, "File", "Load Translations...")
    menu.add(app.open_index, "File", "Load Index...")
    menu.add_separator("File")
    menu.add(app.close, "File", "Close")
    menu.add(app.config_editor, "Tools", "Edit Configuration...")
    menu.add(app.custom_index, "Tools", "Make Index...")
    menu.add(app.debug_console, "Debug", "Open Console...")
    menu.add(app.debug_tree, "Debug", "View Object Tree...")
    app.set_enabled(False)
    app.show()
    # Some object references must be saved in an attribute or else Qt will disconnect the signals upon scope exit.
    app.sys_refs = [exc_man, exc_hook]
    return app

import pkgutil
from typing import Callable, Sequence

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.analysis import TranslationFilter
from spectra_lexer.console.qt import ConsoleDialog
from spectra_lexer.gui import GUILayer, GUIOptions, GUIOutput
from spectra_lexer.objtree.main import NamespaceTreeDialog
from spectra_lexer.qt import WINDOW_ICON_PATH
from spectra_lexer.qt.config import ConfigDialog
from spectra_lexer.qt.display import DisplayController, DisplayPageData
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeDialog
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchController
from spectra_lexer.qt.system import QtTaskExecutor, QtExceptionHook
from spectra_lexer.qt.window import WindowController
from spectra_lexer.translations import ExamplesDict, TranslationsDict, TranslationsIO
from spectra_lexer.util.config import SimpleConfigDict
from spectra_lexer.util.exception import ExceptionManager


class GUILayerExtended(GUILayer):
    """ User GUI actions that may require higher permissions."""

    def __init__(self, io:TranslationsIO, examples_path:str, cfg_path:str, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._io = io
        self._examples_path = examples_path  # User examples index file path.
        self._config = SimpleConfigDict(cfg_path, "app_qt")
        self._last_translations = {}

    def set_translations(self, translations:TranslationsDict) -> None:
        """ Send a new translations dict to the search engine. Keep a copy in case we need to make an index. """
        self._last_translations = translations
        self._search_engine.set_translations(translations)

    def load_translations(self, *filenames:str) -> None:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = self._io.load_json_translations(*filenames)
        self.set_translations(translations)

    def set_examples(self, examples:ExamplesDict) -> None:
        """ Send a new examples index dict to the search engine. """
        self._search_engine.set_examples(examples)

    def load_examples(self, filename:str) -> None:
        """ Load an examples index from a JSON file. """
        examples = self._io.load_json_examples(filename)
        self.set_examples(examples)

    def load_start_examples(self) -> None:
        """ Load the startup examples index. Ignore I/O errors since it may be missing. """
        try:
            self.load_examples(self._examples_path)
        except OSError:
            pass

    def compile_examples(self, size:int) -> None:
        """ Run the lexer on all translations with an optional <size> filter and look at the top-level rule IDs.
            Make a index with examples of every translation that used each built-in rule and set it as active.
            If a <filename> is given, save the index as JSON at the end. """
        index = self._analyzer.compile_index(self._last_translations.items(), size=size)
        examples = {r_id: dict(pairs) for r_id, pairs in index.items()}
        self.set_examples(examples)
        self._io.save_json_examples(self._examples_path, examples)

    def options(self) -> GUIOptions:
        return GUIOptions(self._config)

    def update_config(self, options:dict) -> None:
        self._config.update(options)
        self._config.write()

    def load_config(self) -> bool:
        """ Load the config file. If missing, create it with default values and return True. """
        is_missing = not self._config.read()
        if is_missing:
            options = {key: getattr(GUIOptions, key) for key, *_ in GUIOptions.CFG_OPTIONS}
            self.update_config(options)
        return is_missing


class QtGUIApplication:
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, gui:GUILayerExtended, tasks:QtTaskExecutor, window:WindowController,
                 menu:MenuController, search:SearchController, display:DisplayController) -> None:
        self._gui = gui
        self._tasks = tasks
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display

    def _get_options(self) -> GUIOptions:
        """ Add all values that may be needed by the steno engine as options in precedence order. """
        opts = self._gui.options()
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
        self._gui.set_options(opts)
        out = self._gui.search(pattern, pages)
        self._update_gui(out)

    def gui_query(self, keys_or_seq:Sequence[str], letters:str, strict:bool=None) -> None:
        """ Run a lexer query and update the GUI with any results. """
        opts = self._get_options()
        if strict is not None:
            opts.lexer_strict_mode = strict
        self._gui.set_options(opts)
        out = self._gui.query(keys_or_seq, letters)
        self._update_gui(out)

    def gui_search_examples(self, link_ref:str) -> None:
        """ Run an example search and update the GUI with any results. """
        opts = self._get_options()
        self._gui.set_options(opts)
        out = self._gui.search_examples(link_ref)
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

    def _set_async_mode(self, enabled:bool, status:str=None) -> None:
        """ Set the GUI enabled mode with an optional message when GUI-blocking operations are running. """
        self.set_enabled(enabled)
        if status is not None:
            self.set_status(status)

    def run_async(self, func:Callable, *args, msg_start:str=None, msg_finish:str=None) -> None:
        """ Run a blocking task on another thread. Disable the window controls and show <msg_start> first.
            Queue a callback that will re-enable the controls and show <msg_finish> when the task is done.
            GUI events may misbehave unless explicitly processed before the async thread takes the GIL. """
        q_app = QApplication.instance()
        q_app.processEvents()
        self._tasks.on_main(self._set_async_mode, False, msg_start)
        self._tasks.on_worker(func, *args)
        self._tasks.on_main(self._set_async_mode, True, msg_finish)

    def _on_ready(self) -> None:
        """ When all major resources are ready, load the config and connect the GUI callbacks.
            Present an index generation dialog if this is the first time the program has been run. """
        is_first_run = self._gui.load_config()
        self._search.connect_signals(self.gui_search, self.gui_query)
        self._display.connect_signals(self.gui_search_examples, self.gui_query)
        if is_first_run:
            self.confirm_startup_index()

    def start(self, loader:Callable, *args) -> None:
        """ Load initial data asynchronously on a new thread to avoid blocking the GUI. """
        self._tasks.start()
        self.run_async(loader, *args, msg_start="Loading...", msg_finish="Loading complete.")
        self._tasks.on_main(self._on_ready)

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._window.open_files("Load Translations", "json")
        if filenames:
            self.run_async(self._gui.load_translations, *filenames,
                           msg_start="Loading files...", msg_finish="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._window.open_file("Load Index", "json")
        if filename:
            self.run_async(self._gui.load_examples, filename,
                           msg_start="Loading file...", msg_finish="Loaded index from file dialog.")

    def _config_edited(self, options:dict) -> None:
        self._gui.update_config(options)
        self.set_status("Configuration saved.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._window.open_dialog(ConfigDialog)
        if dialog is not None:
            opts = self._gui.options()
            for key, name, description in GUIOptions.CFG_OPTIONS:
                value = getattr(opts, key)
                dialog.add_option(key, value, "General", name, description)
                dialog.call_on_options_accept(self._config_edited)
            dialog.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.run_async(self._gui.compile_examples, size,
                       msg_start="Making new index...", msg_finish="Successfully created index!")

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

    def on_exception(self, exc:BaseException) -> None:
        """ Store unhandled exceptions and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        self.set_enabled(True)


def build_app(gui:GUILayerExtended, logger:Callable[[str], None]) -> QtGUIApplication:
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
    display = DisplayController(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption,
                                ui.w_slider, ui.w_link_examples, ui.w_link_save)
    app = QtGUIApplication(gui, tasks, window, menu, search, display)
    exc_man.add_logger(display.show_traceback)
    exc_man.add_handler(app.on_exception)
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
    # Some object references must be saved in an attribute or else Qt will disconnect the signals upon scope exit.
    app.sys_refs = [exc_man, exc_hook]
    return app

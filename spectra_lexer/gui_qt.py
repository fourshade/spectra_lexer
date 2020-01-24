""" Main module for the interactive Qt GUI application. """

import pkgutil
import sys
from typing import Callable

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.app import StenoApplication, StenoGUIOutput
from spectra_lexer.base import Spectra
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
from spectra_lexer.util.exception import ExceptionManager


class QtGUIApplication(StenoApplication):
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, async_dsp:QtAsyncDispatcher, window:WindowController,
                 menu:MenuController, search:SearchController, display:DisplayController, *args) -> None:
        """ Connect all GUI inputs to their callbacks. """
        super().__init__(*args)
        self._async_dsp = async_dsp
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        menu.add(self.open_translations, "File", "Load Translations...")
        menu.add(self.open_index, "File", "Load Index...")
        menu.add(self.close, "File", "Close", after_sep=True)
        menu.add(self.config_editor, "Tools", "Edit Configuration...")
        menu.add(self.custom_index, "Tools", "Make Index...")
        menu.add(self.debug_console, "Debug", "Open Console...")
        menu.add(self.debug_tree, "Debug", "View Object Tree...")
        search.call_on_search(self.on_search)
        search.call_on_query(self.on_query)
        display.call_on_query(self.on_query)
        display.call_on_example_search(self.on_search_examples)

    def on_loaded(self, *_) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        if self.is_first_run:
            self.confirm_startup_index()

    def on_search(self, pattern:str, pages:int, **options) -> None:
        """ Run a translation search and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_search(pattern, pages, **options)
        self._update_gui(out)

    def on_query(self, *args, **options) -> None:
        """ Run a lexer query and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_query(*args, **options)
        self._update_gui(out)

    def on_search_examples(self, link_ref:str, **options) -> None:
        """ Run an example search and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_search_examples(link_ref, **options)
        self._update_gui(out)

    def _update_options(self, options:dict) -> None:
        """ Add all GUI values that may be needed by the steno engine as options. """
        options.update(search_mode_strokes=self._search.get_mode_strokes(),
                       search_mode_regex=self._search.get_mode_regex(),
                       board_aspect_ratio=self._display.get_board_ratio(),
                       board_show_compound=self._display.get_board_compound(),
                       board_show_letters=self._display.get_board_letters())

    def _update_gui(self, out:StenoGUIOutput) -> None:
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

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._window.open_files("Load Translations", "json")
        if filenames:
            self.run_async(self.load_translations, *filenames,
                           msg_start="Loading files...", msg_done="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._window.open_file("Load Index", "json")
        if filename:
            self.run_async(self.load_examples, filename,
                           msg_start="Loading file...", msg_done="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dialog = self._window.open_dialog(ConfigDialog)
        if dialog is not None:
            dialog.call_on_options_accept(self._update_config)
            for item in self._config.info():
                dialog.add_option(item.key, item.value, item.title, item.name, item.description)
            dialog.show()

    def _update_config(self, options:dict) -> None:
        self.run_async(self.set_config, options, msg_done="Configuration saved.")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index()

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog(IndexSizeDialog)
        if dialog is not None:
            dialog.call_on_size_accept(self._make_index)
            dialog.setup(RTFCREDict.FILTER_SIZES)
            dialog.show()

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.run_async(self.make_index, size, msg_start="Making new index...", msg_done="Successfully created index!")

    def debug_console(self) -> None:
        """ Create and show an interpreter console dialog. """
        dialog = self._window.open_dialog(ConsoleDialog)
        if dialog is not None:
            namespace = self.console_vars()
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

    def run_async(self, func:Callable, *args, callback:Callable=None, msg_start:str=None, msg_done:str=None) -> None:
        """ Start a blocking async task. If <msg_start> is not None, show it and disable the window controls.
            Make a callback that will re-enable the controls and show <msg_done> when the task is done.
            GUI events may misbehave unless explicitly processed before the async thread takes the GIL. """
        qt_app = QApplication.instance()
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
        qt_app.processEvents()
        self._async_dsp.dispatch(func, *args, on_start=on_task_start, on_finish=on_task_finish)

    def on_exception(self, exc:BaseException) -> None:
        """ Store unhandled exceptions and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        self.set_enabled(True)


class SpectraQt(Spectra):
    """ Start the interactive GUI application. """

    ICON_PATH = __package__, 'qt/icon.svg'  # Package and relative file path for window icon.

    def build_app(self) -> QtGUIApplication:
        """ Build the app with all components necessary to operate the GUI. """
        exc_man = ExceptionManager()
        exc_hook = QtExceptionHook(chain_hooks=False)
        exc_hook.connect(exc_man.on_exception)
        logger = self.build_logger()
        exc_man.add_logger(lambda s: logger.log('EXCEPTION\n' + s))
        async_dsp = QtAsyncDispatcher()
        w_window = QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        window = WindowController(w_window)
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        window.set_icon(icon_data)
        menu = MenuController(ui.w_menubar)
        search = SearchController.from_widgets(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController.from_widgets(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption, ui.w_slider)
        exc_man.add_logger(display.show_traceback)
        config = self.build_config()
        engine = self.build_engine()
        app = QtGUIApplication(async_dsp, window, menu, search, display, config, engine)
        exc_man.add_handler(app.on_exception)
        app.set_enabled(False)
        app.set_status("Loading...")
        app.show()
        # These objects must be saved on attributes or else Qt will disconnect the signals upon scope exit.
        app.exc_man = exc_man
        app.exc_hook = exc_hook
        return app

    def load_app_async(self, app:QtGUIApplication) -> None:
        """ Load heavy data asynchronously on a new thread to avoid blocking the GUI. """
        app.run_async(self.load_app, app, callback=app.on_loaded, msg_start="Loading...", msg_done="Loading complete.")

    def run(self) -> int:
        """ Create a QApplication before building any of the GUI. """
        qt_app = QApplication(sys.argv)
        app = self.build_app()
        self.load_app_async(app)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


gui_main = SpectraQt.main

if __name__ == '__main__':
    sys.exit(gui_main())

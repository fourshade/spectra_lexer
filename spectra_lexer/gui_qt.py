""" Main module for the interactive Qt GUI application. """

import pkgutil
import sys
from typing import Callable

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer.app import StenoApplication, StenoGUIOutput
from spectra_lexer.base import Spectra
from spectra_lexer.debug import DebugData, DebugDataFactory, package
from spectra_lexer.qt.config import ConfigTool
from spectra_lexer.qt.console import ConsoleTool
from spectra_lexer.qt.display import DisplayController, DisplayPageData
from spectra_lexer.qt.index import INDEX_STARTUP_MESSAGE, IndexSizeTool
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.objtree import ObjectTreeColumn, ObjectTreeItem, ObjectTreeItemModel, ObjectTreeTool
from spectra_lexer.qt.search import SearchController
from spectra_lexer.qt.svg import SVGIconRenderer
from spectra_lexer.qt.system import QtAsyncDispatcher, QtExceptionHook
from spectra_lexer.qt.window import WindowController
from spectra_lexer.resource import RTFCREDict
from spectra_lexer.util.exception import ExceptionManager


class KeyColumn(ObjectTreeColumn):
    """ Column 0 is the primary tree item with the key, icon, and children. Possible icons are based on type. """

    def __init__(self, *args, icons:SVGIconRenderer=None) -> None:
        super().__init__(*args)
        self._icons = icons or SVGIconRenderer()  # Renders icons corresponding to data types.

    def format_item(self, item:ObjectTreeItem, data:DebugData) -> None:
        item.set_color(*data.color)
        item.set_text(data.key_text)
        item.set_tooltip(data.key_tooltip)
        item.set_edit_cb(data.key_edit)
        item.set_children(data)
        icon_xml = data.icon_data
        if icon_xml:
            icon = self._icons.render(icon_xml)
            item.set_icon(icon)


class TypeColumn(ObjectTreeColumn):
    """ Column 1 contains the type of object, item count, and/or a tooltip detailing the MRO. """

    def format_item(self, item:ObjectTreeItem, data:DebugData) -> None:
        item.set_color(*data.color)
        text = data.type_text
        count = data.item_count
        if count is not None:
            text += f' - {count} item{"s" * (count != 1)}'
        item.set_text(text)
        item.set_tooltip(data.type_graph)


class ValueColumn(ObjectTreeColumn):
    """ Column 2 contains the string value of the object. It may be edited if mutable. """

    def format_item(self, item:ObjectTreeItem, data:DebugData) -> None:
        item.set_color(*data.color)
        item.set_text(data.value_text)
        item.set_tooltip(data.value_tooltip)
        item.set_edit_cb(data.value_edit)


class QtGUIApplication(StenoApplication):
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: BaseException = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, async_dsp:QtAsyncDispatcher, window:WindowController,
                 menu:MenuController, search:SearchController, display:DisplayController, *args) -> None:
        self._async_dsp = async_dsp
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        super().__init__(*args)

    def connect_gui(self) -> None:
        """ Connect the exception hook and all GUI inputs to their callbacks. """
        self._menu.add(self.open_translations, "File", "Load Translations...")
        self._menu.add(self.open_index, "File", "Load Index...")
        self._menu.add(self.close, "File", "Close", after_sep=True)
        self._menu.add(self.config_editor, "Tools", "Edit Configuration...")
        self._menu.add(self.custom_index, "Tools", "Make Index...")
        self._menu.add(self.debug_console, "Debug", "Open Console...")
        self._menu.add(self.debug_tree, "Debug", "View Object Tree...")
        self._search.call_on_search(self.on_search)
        self._search.call_on_query(self.on_query)
        self._display.call_on_query(self.on_query)
        self._display.call_on_example_search(self.on_search_examples)

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
            translation = [display_data.keys, display_data.letters]
            default_item = (DisplayPageData.DEFAULT_KEY, display_data.default_page)
            input_items = [default_item, *display_data.pages_by_ref.items()]
            output_dict = {}
            for ref, page in input_items:
                graphs = [page.graph, page.intense_graph]
                board_xml = page.board.encode('utf-8')
                output_dict[ref] = DisplayPageData(graphs, page.caption, board_xml, page.rule_id)
            self._search.select_translation(*translation)
            self._display.set_translation(*translation)
            self._display.set_pages(output_dict)

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
        dialog = self._window.open_dialog("Spectra Configuration", 250, 300)
        if dialog is not None:
            config_tool = ConfigTool(dialog)
            for item in self._config.info():
                config_tool.add_option(item.key, item.value, item.title, item.name, item.description)
            config_tool.call_on_options_accept(self._update_config)
            config_tool.display()
            dialog.tool_ref = config_tool

    def _update_config(self, options:dict) -> None:
        self.run_async(self.set_config, options, msg_done="Configuration saved.")

    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index()

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog("Choose Index Size", 360, 320)
        if dialog is not None:
            index_tool = IndexSizeTool(dialog)
            index_tool.call_on_size_accept(self._make_index)
            index_tool.set_sizes(RTFCREDict.FILTER_SIZES)
            index_tool.display()
            dialog.tool_ref = index_tool

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.run_async(self.make_index, size, msg_start="Making new index...", msg_done="Successfully created index!")

    def debug_console(self) -> None:
        """ Create an interpreter console instance and show the debug console dialog.
            Save the console reference on an attribute to avoid garbage collection. """
        dialog = self._window.open_dialog("Python Console", 680, 480)
        if dialog is not None:
            console_tool = ConsoleTool(dialog)
            stream = console_tool.to_stream()
            console = self.open_console(stream)
            console.print_opening()
            console_tool.console_ref = console
            console_tool.call_on_new_line(console.send)
            console_tool.display()

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        dialog = self._window.open_dialog("Python Object Tree View", 600, 450)
        if dialog is not None:
            objtree_tool = ObjectTreeTool(dialog)
            debug_vars = {**vars(self), "modules": package.modules()}
            factory = DebugDataFactory()
            factory.load_icons()
            root_data = factory.generate(debug_vars)
            root_item = ObjectTreeItem()
            root_item.set_children(root_data)
            key_col = KeyColumn("Name")
            type_col = TypeColumn("Type/Item Count")
            value_col = ValueColumn("Value")
            item_model = ObjectTreeItemModel(root_item, [key_col, type_col, value_col])
            objtree_tool.set_model(item_model)
            objtree_tool.display()

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
            Make a callback that will re-enable the controls and show <msg_done> when the task is done. """
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
        self._excman = excman = ExceptionManager()
        exc_hook = QtExceptionHook(chain_hooks=False)
        exc_hook.connect(excman.on_exception)
        logger = self.build_logger()
        excman.add_logger(lambda s: logger.log('EXCEPTION\n' + s))
        async_dsp = QtAsyncDispatcher()
        w_window = QMainWindow()
        ui = Ui_MainWindow()
        ui.setupUi(w_window)
        # Load the main window icon from a bytes object.
        icon_data = pkgutil.get_data(*self.ICON_PATH)
        icon = SVGIconRenderer().render(icon_data)
        w_window.setWindowIcon(icon)
        window = WindowController(w_window)
        menu = MenuController(ui.w_menubar)
        search = SearchController.from_widgets(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
        display = DisplayController.from_widgets(ui.w_title, ui.w_graph, ui.w_board, ui.w_caption, ui.w_slider)
        excman.add_logger(display.show_traceback)
        config = self.build_config()
        engine = self.build_engine()
        app = QtGUIApplication(async_dsp, window, menu, search, display, config, engine)
        excman.add_handler(app.on_exception)
        app.connect_gui()
        app.show()
        return app

    def load_app_async(self, app:QtGUIApplication) -> None:
        """ Load heavy data asynchronously on a new thread to avoid blocking the GUI. """
        # GUI events may misbehave unless explicitly processed first.
        qt_app = QApplication.instance()
        qt_app.processEvents()
        app.run_async(self.load_app, app, callback=app.on_loaded, msg_start="Loading...", msg_done="Loading complete.")

    def run(self) -> int:
        """ Create a QApplication before building any of the GUI. """
        qt_app = QApplication(sys.argv)
        app = self.build_app()
        self.load_app_async(app)
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


gui = SpectraQt.main

if __name__ == '__main__':
    sys.exit(gui())

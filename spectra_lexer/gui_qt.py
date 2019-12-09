""" Main module for the interactive GUI application. """

import pkgutil
import sys
from traceback import format_exception
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
from spectra_lexer.qt.system import QtAsyncDispatcher, QtExceptionTrap
from spectra_lexer.qt.window import WindowController
from spectra_lexer.resource import RTFCREDict
from spectra_lexer.util.log import StreamLogger


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


def trap_exceptions(func:Callable) -> Callable[..., None]:
    """ Set an exception trap on GUI menu commands and input handlers. """
    def trapped_call(self, *args, **kwargs) -> None:
        with self._exc_trap:
            func(self, *args, **kwargs)
    return trapped_call


class QtGUIApplication(StenoApplication):
    """ Top-level object for Qt GUI operations. Contains all components for the application as a whole. """

    last_exception: Exception = None  # Most recently trapped exception, saved for debug tools.

    def __init__(self, logger:StreamLogger, window:WindowController,
                 menu:MenuController, search:SearchController, display:DisplayController, *args) -> None:
        self._log = logger.log
        self._exc_trap = exc_trap = QtExceptionTrap()
        self._async_call = QtAsyncDispatcher(exc_trap).dispatch
        self._window = window
        self._menu = menu
        self._search = search
        self._display = display
        self.show = window.show
        self.close = window.close
        self.set_status = display.set_status
        exc_trap.connect(self._handle_exception)
        super().__init__(*args)

    def on_loaded(self, *_) -> None:
        """ On first start, present a dialog for the user to make a default-sized index on accept. """
        if self.is_first_run:
            self.confirm_startup_index()

    @trap_exceptions
    def on_search(self, *args, **options) -> None:
        """ Run a translation search and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_search(*args, **options)
        self._update_gui(out)

    @trap_exceptions
    def on_query(self, *args, **options) -> None:
        """ Run a lexer query and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_query(*args, **options)
        self._update_gui(out)

    @trap_exceptions
    def on_search_examples(self, *args, **options) -> None:
        """ Run an example search and update the GUI with any results. """
        self._update_options(options)
        out = self.gui_search_examples(*args, **options)
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

    @trap_exceptions
    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = self._window.open_files("Load Translations", "json")
        if filenames:
            self.run_async(self.load_translations, *filenames, msg_done="Loaded translations from file dialog.")

    @trap_exceptions
    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = self._window.open_file("Load Index", "json")
        if filename:
            self.run_async(self.load_examples, filename, msg_done="Loaded index from file dialog.")

    @trap_exceptions
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
        self.run_async(self.set_config, options, disable=False, msg_done="Configuration saved.")

    @trap_exceptions
    def confirm_startup_index(self) -> None:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        if self._window.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE):
            self._make_index()

    @trap_exceptions
    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dialog = self._window.open_dialog("Choose Index Size", 360, 320)
        if dialog is not None:
            index_tool = IndexSizeTool(dialog)
            index_tool.call_on_size_accept(self._make_index)
            info = RTFCREDict.FilterSizes
            sizes = [info.MINIMUM_SIZE, info.SMALL_SIZE, info.MEDIUM_SIZE, info.LARGE_SIZE, info.MAXIMUM_SIZE]
            index_tool.set_sizes(sizes)
            index_tool.display()
            dialog.tool_ref = index_tool

    def _make_index(self, size:int=None) -> None:
        """ Make a custom-sized index. Disable the GUI while processing and show a success message when done. """
        self.set_status("Making new index...")
        self.run_async(self.make_index, size, msg_done="Successfully created index!")

    @trap_exceptions
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

    @trap_exceptions
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

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are running. """
        self._menu.set_enabled(enabled)
        self._search.set_enabled(enabled)
        self._display.set_enabled(enabled)

    def run_async(self, func:Callable, *args, callback=None, disable=True, msg_done:str=None) -> None:
        """ Start a blocking async task. Most require disabling the window controls.
            Make a callback that will re-enable the controls and show <msg_done> when the task is done. """
        if disable:
            self.set_enabled(False)
        def on_task_finish(val) -> None:
            self.set_status(msg_done)
            self.set_enabled(True)
            if callback is not None:
                callback(val)
        self._async_call(func, *args, callback=on_task_finish)

    def _handle_exception(self, exc:Exception, max_frames=20) -> None:
        """ Format, log, and display a stack trace for any thrown exception.
            Store the exception and enable all widgets afterward to allow debugging. """
        self.last_exception = exc
        tb_text = "".join(format_exception(type(exc), exc, exc.__traceback__, limit=max_frames))
        self._log('EXCEPTION\n' + tb_text)
        self._display.show_traceback(tb_text)
        self.set_enabled(True)


class SpectraQt(Spectra):
    """ Main factory for the Qt GUI application. """

    ICON_PATH = __package__, 'qt/icon.svg'  # Package and relative file path for window icon.

    def build(self) -> QtGUIApplication:
        """ Build all components necessary to operate the GUI. """
        logger = self.build_logger()
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
        config = self.build_config()
        engine = self.build_engine()
        app = QtGUIApplication(logger, window, menu, search, display, config, engine)
        menu.add(app.open_translations, "File", "Load Translations...")
        menu.add(app.open_index, "File", "Load Index...")
        menu.add(app.close, "File", "Close", after_sep=True)
        menu.add(app.config_editor, "Tools", "Edit Configuration...")
        menu.add(app.custom_index, "Tools", "Make Index...")
        menu.add(app.debug_console, "Debug", "Open Console...")
        menu.add(app.debug_tree, "Debug", "View Object Tree...")
        search.call_on_search(app.on_search)
        search.call_on_query(app.on_query)
        display.call_on_query(app.on_query)
        display.call_on_example_search(app.on_search_examples)
        # Load the heavy app data asynchronously on a new thread to avoid blocking the GUI.
        app.set_status("Loading...")
        app.run_async(self.load_app, app, callback=app.on_loaded, msg_done="Loading complete.")
        app.show()
        return app

    def run(self) -> int:
        """ Create a QApplication and load the GUI in standalone mode. """
        qt_app = QApplication(sys.argv)
        # The returned object must be assigned to a dummy local, or else Qt will garbage-collect it and crash...
        _ = self.build()
        # After everything is loaded, start a GUI event loop and run it indefinitely.
        return qt_app.exec_()


gui = SpectraQt.main

if __name__ == '__main__':
    sys.exit(gui())

""" Main module for the Qt GUI application. """

import pkgutil
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.config.main import QtConfigManager
from spectra_lexer.config.spec import BoolOption, ConfigSpec, IntOption
from spectra_lexer.engine import Engine, EngineOptions
from spectra_lexer.gui_qt import CONFIG_SECTION, QtGUIApplication
from spectra_lexer.qt import ICON_PACKAGE, ICON_PATH
from spectra_lexer.qt.board import BoardPanel
from spectra_lexer.qt.dialog import DialogManager
from spectra_lexer.qt.graph import GraphPanel
from spectra_lexer.qt.main_window_ui import Ui_MainWindow
from spectra_lexer.qt.menu import MenuController
from spectra_lexer.qt.search import SearchPanel
from spectra_lexer.qt.system import QtTaskExecutor
from spectra_lexer.qt.title import TitleDisplay
from spectra_lexer.qt.window import WindowController
from spectra_lexer.util.exception import CompositeExceptionHandler, ExceptionLogger


def get_config_spec() -> ConfigSpec:
    """ Return a spec for engine options which should be saved in a CFG file. """
    return ConfigSpec(name=CONFIG_SECTION, title='General', options=[
        IntOption(name="search_match_limit",
                  default=EngineOptions.search_match_limit,
                  title="Match Limit",
                  description="Maximum number of matches returned on one page of a search."),
        BoolOption(name="lexer_strict_mode",
                   default=EngineOptions.lexer_strict_mode,
                   title="Strict Mode",
                   description="Only return lexer results that match every key in a translation."),
        BoolOption(name="graph_compressed_layout",
                   default=EngineOptions.graph_compressed_layout,
                   title="Compressed Layout",
                   description="Compress the graph layout vertically to save space.")
    ])


def build_app(spectra:Spectra) -> QtGUIApplication:
    """ Build the interactive Qt GUI application with all necessary components. """
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    translations_paths = spectra.translations_paths
    index_path = spectra.index_path
    engine = Engine(io, search_engine, analyzer, graph_engine, board_engine, translations_paths, index_path)
    cfg_path = spectra.cfg_path
    spec = get_config_spec()
    config = QtConfigManager(cfg_path, [spec])
    tasks = QtTaskExecutor()
    w_window = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(w_window)
    dialogs = DialogManager(w_window)
    window = WindowController(w_window)
    icon_data = pkgutil.get_data(ICON_PACKAGE, ICON_PATH)
    window.set_icon(icon_data)
    menu = MenuController(ui.w_menubar)
    title = TitleDisplay(ui.w_title)
    search = SearchPanel(ui.w_input, ui.w_matches, ui.w_mappings, ui.w_strokes, ui.w_regex)
    graph = GraphPanel(ui.w_graph)
    board = BoardPanel(ui.w_board, ui.w_caption, ui.w_slider, ui.w_link_save, ui.w_link_examples)
    app = QtGUIApplication(engine, config, tasks, dialogs, window, menu, title, search, graph, board)
    exc_handler = CompositeExceptionHandler()
    exc_logger = ExceptionLogger(spectra.logger.log)
    exc_handler.add(exc_logger)
    exc_handler.add(app.on_exception)
    sys.excepthook = exc_handler
    f_menu = menu.get_section("File")
    f_menu.addItem(app.open_translations, "Load Translations...")
    f_menu.addItem(app.open_index, "Load Index...")
    f_menu.addSeparator()
    f_menu.addItem(app.close, "Close")
    t_menu = menu.get_section("Tools")
    t_menu.addItem(app.config_editor, "Edit Configuration...")
    t_menu.addItem(app.custom_index, "Make Index...")
    d_menu = menu.get_section("Debug")
    d_menu.addItem(app.debug_console, "Open Console...")
    d_menu.addItem(app.debug_tree, "View Object Tree...")
    return app


def main() -> int:
    """ In standalone mode, we must create a QApplication and run a GUI event loop indefinitely. """
    q_app = QApplication(sys.argv)
    opts = SpectraOptions("Run Spectra as a standalone GUI application.")
    spectra = Spectra(opts)
    app = build_app(spectra)
    app.start()
    return q_app.exec_()


if __name__ == '__main__':
    sys.exit(main())

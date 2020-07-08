""" Main module for the standalone Qt GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.gui_engine import GUIEngine
from spectra_lexer.gui_qt import build_app
from spectra_lexer.gui_ext import GUIExtension


def main() -> int:
    """ In standalone mode, we must create a QApplication before building any of the GUI. """
    q_app = QApplication(sys.argv)
    opts = SpectraOptions("Run Spectra as a standalone GUI application.")
    spectra = Spectra.compile(opts)
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    log = spectra.logger.log
    translations_paths = spectra.translations_paths
    index_path = spectra.index_path
    cfg_path = spectra.cfg_path
    gui_engine = GUIEngine(search_engine, analyzer, graph_engine, board_engine)
    gui_ext = GUIExtension(io, search_engine, analyzer, translations_paths, index_path, cfg_path)
    app = build_app(gui_engine, gui_ext, log)
    app.start(gui_ext.load_initial)
    # After everything is loaded, start a GUI event loop and run it indefinitely.
    return q_app.exec_()


if __name__ == '__main__':
    sys.exit(main())

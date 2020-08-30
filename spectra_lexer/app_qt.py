""" Main module for the Qt GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.engine import Engine
from spectra_lexer.gui_qt import build_gui_app, QtGUIApplication
from spectra_lexer.util.exception import CompositeExceptionHandler, ExceptionLogger


def build_app(spectra:Spectra) -> QtGUIApplication:
    """ Build the interactive Qt GUI application with all necessary components. """
    exc_handler = CompositeExceptionHandler()
    exc_logger = ExceptionLogger(spectra.logger.log)
    exc_handler.add(exc_logger)
    sys.excepthook = exc_handler
    io = spectra.resource_io
    search_engine = spectra.search_engine
    analyzer = spectra.analyzer
    graph_engine = spectra.graph_engine
    board_engine = spectra.board_engine
    translations_paths = spectra.translations_paths
    index_path = spectra.index_path
    engine = Engine(io, search_engine, analyzer, graph_engine, board_engine, translations_paths, index_path)
    cfg_path = spectra.cfg_path
    app = build_gui_app(engine, cfg_path)
    exc_handler.add(app.on_exception)
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

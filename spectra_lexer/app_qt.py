""" Main module for the standalone Qt GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import SpectraOptions
from spectra_lexer.gui_engine import GUIEngine
from spectra_lexer.gui_qt import build_app
from spectra_lexer.gui_ext import GUIExtension


def main() -> int:
    """ In standalone mode, we must create a QApplication before building any of the GUI. """
    q_app = QApplication(sys.argv)
    opts = SpectraOptions("Run Spectra as a standalone GUI application.")
    spectra = opts.compile()
    index_path = opts.index_path()
    cfg_path = opts.config_path()
    gui_engine = GUIEngine(spectra.search_engine, spectra.analyzer, spectra.graph_engine, spectra.board_engine)
    gui_ext = GUIExtension(spectra.translations_io, spectra.search_engine, spectra.analyzer, index_path, cfg_path)
    app = build_app(gui_engine, gui_ext, spectra.log)
    translations_paths = opts.translations_paths()
    def load_all() -> None:
        gui_ext.load_translations(*translations_paths)
        gui_ext.load_start_examples()
        gui_ext.load_config()
    app.start(load_all)
    # After everything is loaded, start a GUI event loop and run it indefinitely.
    return q_app.exec_()


if __name__ == '__main__':
    sys.exit(main())

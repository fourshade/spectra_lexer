""" Main module for the standalone Qt GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Spectra
from spectra_lexer.gui_qt import QtGUIApplication
from spectra_lexer.util.cmdline import CmdlineOptions


def main() -> int:
    """ In standalone mode, we must create a QApplication before building any of the GUI. """
    q_app = QApplication(sys.argv)
    opts = CmdlineOptions("Run Spectra as a standalone GUI application.")
    spectra = Spectra(opts)
    engine = spectra.build_engine()
    index_path = spectra.index_path()
    cfg_path = spectra.config_path()
    app = QtGUIApplication.build(engine, spectra.log, index_path, cfg_path)
    translations_paths = spectra.translations_paths()
    app.run_async(engine.load_translations, *translations_paths)
    app.load_user_files()
    # After everything is loaded, start a GUI event loop and run it indefinitely.
    return q_app.exec_()


if __name__ == '__main__':
    sys.exit(main())

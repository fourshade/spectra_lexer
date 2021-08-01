""" Main module for the Qt GUI application. """

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Spectra, SpectraOptions
from spectra_lexer.app_qt import build_app


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

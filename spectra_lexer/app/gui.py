import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import core, gui_qt, interactive
from spectra_lexer.app import Application


def main() -> None:
    """ Top-level function for operation of the Spectra program *by itself* with the standard GUI. """
    # Assemble and start all components. The GUI components must be first in the list so that they start before others.
    qt_app = QApplication(sys.argv)
    app = Application(gui_qt, core, interactive)
    app.start()
    # Run the GUI event loop indefinitely.
    qt_app.exec_()


if __name__ == '__main__':
    main()

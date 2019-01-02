import sys
from typing import Iterable

from PyQt5.QtWidgets import QApplication

from spectra_lexer import SpectraComponent
from spectra_lexer.app import SpectraApplication
from spectra_lexer.gui_qt.window import MainWindow


class GUIQtApplication(SpectraApplication):
    """ Class for operation of the Spectra program in a GUI by itself. """

    def __init__(self, *components:SpectraComponent):
        """ The main window distributes tasks among the Qt widgets in the main window. """
        super().__init__(*MainWindow().partition(), *components)

    def start(self, argv:Iterable[str]=()) -> None:
        """ In standalone mode, Plover's dictionaries are loaded by default. """
        super().start(argv)
        self.engine.send("file_load_plover_dicts")


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself with the standard GUI. """
    # For standalone operation, a Qt application object must be created to support the windows.
    qt_app = QApplication(sys.argv)
    app = GUIQtApplication()
    app.start(sys.argv[1:])
    # This function blocks indefinitely after setup to run the GUI.
    qt_app.exec_()


if __name__ == '__main__':
    main()

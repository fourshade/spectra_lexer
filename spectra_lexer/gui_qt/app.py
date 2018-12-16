import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.gui_qt.window import MainWindow
from spectra_lexer.output import OutputFormatter


class GUIQtApplication(SpectraApplication):
    """ Base class for operation of the Spectra program with a GUI. """

    def __init__(self, *components, window:MainWindow, **kwargs):
        # Default GUI support components.
        super().__init__(OutputFormatter(), *window.components, *components, **kwargs)
        # All engine components must be informed of the new window's existence.
        self.engine_call("new_window")


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself with the standard GUI.
        For standalone operation, a Qt application object must be created to support the windows. """
    qt_app = QApplication(sys.argv)
    # All command-line arguments are assumed to be steno dictionary files.
    # If there are no arguments, Plover's dictionaries may be loaded instead.
    # The base window class is currently suitable to be the main standalone GUI.
    GUIQtApplication(window=MainWindow(), dict_files=sys.argv[1:])
    qt_app.exec_()


if __name__ == '__main__':
    main()

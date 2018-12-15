import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.output import OutputFormatter
from spectra_lexer.gui_qt.window import BaseWindow


class GUIQtApplication(SpectraApplication):
    """ Base class for operation of the Spectra program with a GUI. """

    def __new__(cls, **kwargs):
        self = super().__new__(cls, **kwargs)
        # Default GUI support components.
        self.add_children([OutputFormatter()])
        return self

    def set_window(self, window:BaseWindow) -> None:
        """ Set up the window in a separate step. It may be destroyed independently. """
        self.engine.connect(window)
        window.show()
        # All engine components must be informed of the new window's existence.
        self.engine_call("new_window")


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself with the standard GUI.
        For standalone operation, a Qt application object must be created to support the windows. """
    qt_app = QApplication(sys.argv)
    # All command-line arguments are assumed to be steno dictionary files.
    # If there are no arguments, Plover's dictionaries may be loaded instead.
    spectra_app = GUIQtApplication(dict_files=sys.argv[1:])
    # The base window class is currently suitable to be the main standalone GUI.
    spectra_app.set_window(BaseWindow())
    qt_app.exec_()


if __name__ == '__main__':
    main()

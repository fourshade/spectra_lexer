import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from spectra_lexer.app import SpectraApplication
from spectra_lexer.console import ConsoleManager
from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.text import CascadedTextFormatter

# Components specifically used by the GUI. Without the GUI, these components do no good.
GUI_COMPONENTS = [CascadedTextFormatter, ConsoleManager, GUIQt]


class GUIQtApplication(SpectraApplication):
    """ Class for operation of the Spectra program in a GUI by itself. """

    def __init__(self, *components:Component):
        """ The Qt widgets take direct orders from the GUIQt component and its children.
            Other components provide support services for interactive tasks. """
        gui_components = [tp() for tp in GUI_COMPONENTS]
        super().__init__(*gui_components, *components)

    def start(self, *cmd_args:str, **opts) -> None:
        """ In standalone mode, Plover's dictionaries are loaded by default. """
        super().start(*cmd_args, **opts)
        self.engine.call("dict_load_translations")


def main() -> None:
    """ Top-level function for operation of the Spectra program by itself with the standard GUI. """
    # For standalone operation, a Qt application object must be created to support the windows.
    qt_app = QApplication(sys.argv)
    app = GUIQtApplication()
    app.start(*sys.argv[1:])
    # This function blocks indefinitely after setup to run the GUI.
    qt_app.exec_()


if __name__ == '__main__':
    main()

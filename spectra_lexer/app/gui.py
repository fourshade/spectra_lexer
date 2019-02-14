import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.app import SpectraApplication
from spectra_lexer.board import BoardRenderer
from spectra_lexer.console import SpectraConsole
from spectra_lexer.graph import GraphRenderer
from spectra_lexer.gui_qt import GUIQt

# Components specifically used by the GUI. Without the GUI, these components do no good.
GUI_COMPONENTS = [GUIQt,
                  BoardRenderer,
                  GraphRenderer,
                  SpectraConsole]


class GUIQtApplication(SpectraApplication):
    """ Class for operation of the Spectra program in a GUI. """

    def __init__(self, *cls_iter:type):
        """ The Qt widgets take direct orders from the GUIQt component and its children.
            Other components provide support services for interactive tasks. """
        super().__init__(*GUI_COMPONENTS, *cls_iter)

    def start(self, **opts) -> None:
        """ Load the board SVG asset and add the app's engine and components to the console on startup. """
        cvars = {"engine": self.engine, **{c.ROLE: c for c in self.root.components}}
        all_opts = {"board": (), "console_vars": cvars, **opts}
        super().start(**all_opts)


def main() -> None:
    """ Top-level function for operation of the Spectra program *by itself* with the standard GUI. """
    # For standalone operation, a Qt application object must be created to support the windows.
    qt_app = QApplication(sys.argv)
    app = GUIQtApplication()
    # In standalone mode, Plover's dictionaries are loaded by default by providing an empty translations option.
    app.start(translations=())
    # This function blocks indefinitely after setup to run the GUI event loop.
    qt_app.exec_()


if __name__ == '__main__':
    main()

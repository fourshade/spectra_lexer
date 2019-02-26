import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.gui_qt import GUIQtApplication


def main() -> None:
    """ Top-level function for operation of the Spectra program *by itself* with the standard GUI.
        In standalone mode, Plover's dictionaries are loaded by default. """
    # For standalone operation, a Qt application object must be created to support the windows.
    qt_app = QApplication(sys.argv)
    app = GUIQtApplication(gui_evt_proc=qt_app.processEvents)
    app.start()
    # This function blocks indefinitely after setup to run the GUI event loop.
    qt_app.exec_()


if __name__ == '__main__':
    main()

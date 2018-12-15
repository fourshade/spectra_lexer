import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.gui_qt.main_window import MainWindow


def main() -> None:
    """ Main console entry point for the Spectra steno lexer. Should be simple as possible. """
    # All command-line arguments are assumed to be steno dictionary files.
    app = QApplication(sys.argv)
    window = MainWindow(files=sys.argv[1:])
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()

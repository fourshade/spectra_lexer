import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.gui_qt.main_window import MainWindow


def main() -> None:
    """ Main console entry point for the Spectra steno lexer. Should be simple as possible. """
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()

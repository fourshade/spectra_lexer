import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer.plover.compat import PloverEngine, PloverAction
from spectra_lexer.plover.dialog import PloverDialog


def test() -> None:
    """ Entry point for testing the Plover plugin by creating a fake Plover engine. """
    qt_app = QApplication(sys.argv)
    fake_engine = PloverEngine()
    PloverDialog(fake_engine)
    # Execute one of each callback with simple test data, then run the event loop.
    fake_engine.dictionaries_loaded(fake_engine.dictionaries)
    fake_engine.translated((), [PloverAction()])
    qt_app.exec_()


if __name__ == '__main__':
    test()

from collections import namedtuple
import sys
from typing import ClassVar

from PyQt5.QtWidgets import QApplication, QDialog, QWidget

from spectra_lexer.gui_qt import GUIQtApplication
from spectra_lexer.plover.compat import PloverAction, PloverEngine
from spectra_lexer.plover.interface import PloverPluginInterface
from spectra_lexer.utils import nop


class PloverPlugin(QDialog):
    """ Main entry point for the Plover plugin. Non-instantiatable dummy class with parameters required by Plover.
        The actual window returned by __new__ is the standard QMainWindow used by the standalone GUI.
        This class is just a facade, appearing as a QDialog to satisfy Plover's setup requirements. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    # The window and all of its contents are destroyed if it is closed with no referents.
    # The engine's components are relatively expensive to create, so a window reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    window: ClassVar[QWidget] = None

    def __new__(cls, *args):
        """ Only create a new app/window instance on the first call; return the saved instance otherwise.
            The engine is always the first argument passed by Plover. Others are irrelevant. """
        if cls.window is None:
            # The QApplication currently running Plover is required to manually process events.
            evt_proc = QApplication.instance().processEvents
            # The interface to the Plover engine is the only new component needed.
            app = GUIQtApplication(PloverPluginInterface, gui_evt_proc=evt_proc)
            cls.window = app.get_window()
            # To emulate a dialog class, we have to fake a "finished" signal object with a 'connect' attribute.
            cls.window.finished = namedtuple("dummy_signal", "connect")(nop)
            # Translations file loading must be suppressed; we get them from Plover instead.
            app.start(translations_files=None, plover_engine=args[0], show_file_menu=False)
        return cls.window


def plover_test() -> None:
    """ Entry point for testing the Plover plugin by creating a QApplication with a fake Plover engine. """
    qt_app = QApplication(sys.argv)
    fake_engine = PloverEngine()
    PloverPlugin(fake_engine)
    # Execute one of each callback with simple test data.
    fake_engine.dictionaries_loaded(fake_engine.dictionaries)
    fake_engine.translated((), [PloverAction()])
    qt_app.exec_()


if __name__ == '__main__':
    plover_test()

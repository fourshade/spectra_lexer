import sys
from collections import namedtuple
from typing import ClassVar

from PyQt5.QtWidgets import QDialog, QMainWindow

from spectra_lexer import core, gui_qt, interactive, plover
from spectra_lexer.app import Application
from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.utils import nop


class PloverWindow(GUIQt):
    """ The Plover plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    test_mode = Option("cmdline", "plover-test", False, "If True, run the plugin without Plover.")

    @respond_to("run")
    def loop(self) -> MainWindow:
        """ As a plugin, there is already an event loop running somewhere that needs the window we created. """
        if self.test_mode:
            super().loop()
        # To emulate a dialog class, we have to fake a "finished" signal object with a 'connect' attribute.
        self.window.finished = namedtuple("dummy_signal", "connect")(nop)
        return self.window


class PloverDialog(QDialog):
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
    # The app's components are relatively expensive to create, so an app reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    window: ClassVar[QMainWindow] = None

    def __new__(cls, *args):
        """ Only create a new app/window instance on the first call; return the saved instance otherwise. """
        if cls.window is None:
            # Translations file loading must be suppressed; we get them from Plover instead.
            sys.argv.append("--translations-files=IGNORE")
            # The file menu should not be available; clicking the "Exit" button is likely to crash Plover.
            app = Application(gui_qt, PloverWindow, core, interactive, plover)
            # In plugin mode, the GUI event loop isn't run by Spectra, so the Qt window is returned instead.
            cls.window = app.start(plover_args=args, gui_menus=("Tools",))
        return cls.window


def test():
    """ Entry point for testing the Plover plugin by running it with no engine in a standalone configuration. """
    sys.argv.append("--plover-test=True")
    PloverDialog()


if __name__ == '__main__':
    test()

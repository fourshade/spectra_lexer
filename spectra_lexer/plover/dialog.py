from collections import namedtuple
from typing import ClassVar

from PyQt5.QtWidgets import QDialog, QMainWindow

from spectra_lexer import core, gui_qt, interactive, plover
from spectra_lexer.app import Application
from spectra_lexer.utils import nop


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
    # The app's components are relatively exp
    # ensive to create, so an app reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    window: ClassVar[QMainWindow] = None

    def __new__(cls, *args):
        """ Only create a new app/window instance on the first call; return the saved instance otherwise.
            The engine is always the first argument passed by Plover. Others are irrelevant. """
        if cls.window is None:
            app = Application(*gui_qt.COMPONENTS, *core.COMPONENTS, *interactive.COMPONENTS, *plover.COMPONENTS)
            # Translations file loading must be suppressed; we get them from Plover instead.
            # The file menu should not be available; clicking the "Exit" button is likely to crash Plover.
            app.start(translations_files=None, plover_engine=args[0], gui_menus=("Tools",))
            # We need the window from the GUI Qt component section, so search the component dict for it.
            cls.window = app.components["gui_window"].window
            # To emulate a dialog class, we have to fake a "finished" signal object with a 'connect' attribute.
            cls.window.finished = namedtuple("dummy_signal", "connect")(nop)
        return cls.window

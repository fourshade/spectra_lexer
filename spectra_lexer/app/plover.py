from __future__ import annotations
from typing import ClassVar

from PyQt5.QtWidgets import QDialog, QWidget

from spectra_lexer.app import SpectraApplication
from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.plover import PloverPluginInterface
from spectra_lexer.utils import nop


class _FakeSignal:
    """ To emulate a dialog class, we have to fake a "finished" signal. Since the window is never
        really destroyed while Plover is running, this signal would never get triggered anyway. """
    connect = nop


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
        """ Only create a new window instance on the first call; return the saved instance otherwise.
            The engine is always the first argument passed by Plover. Others are irrelevant. """
        if cls.window is None:
            interface = PloverPluginInterface()
            gui = GUIQt()
            cls.window = gui.window
            cls.window.finished = _FakeSignal()
            SpectraApplication(interface, gui).start(plover_engine=args[0], show_menu=False)
        return cls.window

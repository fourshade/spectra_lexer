from typing import ClassVar

from PyQt5.QtCore import pyqtSignal

from spectra_lexer.gui_qt.window import BaseWindow
from spectra_lexer.plover.app import PloverPluginApplication


class PloverPlugin(BaseWindow):
    """ Main entry point for Plover plugin. Must be (or appear to be) a subclass of QDialog. """

    # Class constants required by Plover for toolbar.
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    # To emulate a dialog class, this class must have a finished signal.
    finished = pyqtSignal([])

    # The window and all of its contents are destroyed if it is closed with no referents.
    # The engine's components are relatively expensive to create, so a window reference is kept
    # in the class dictionary and returned on every call after the first, making it a singleton.
    instance: ClassVar[__qualname__] = None
    app: PloverPluginApplication = None

    def __new__(cls, *args):
        """ Only create a new window instance on the first call; return the saved instance otherwise. """
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self, *args):
        """ Only initialize the application on the first call. """
        super().__init__()
        if self.app is None:
            self.app = PloverPluginApplication(window=self, plover_args=args)
        # Hide the menu bar so that the window looks more like a dialog (and can't load dictionaries from disk).
        self.m_menu.setVisible(False)

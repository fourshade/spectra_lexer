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

    # To emulate a dialog class, this object must have a finished signal.
    finished = pyqtSignal([])

    # The window and all of its contents are destroyed if it is allowed to be closed.
    # The engine's components are relatively expensive to create, so a reference is saved
    # in the class dictionary and returned on every call after the first, making it a singleton.
    instance: ClassVar[__qualname__] = None
    app: PloverPluginApplication = None

    def __new__(cls, *args):
        """ Initialize the application on the first call; use the saved instance otherwise. """
        if cls.instance is not None:
            return cls.instance
        self = cls.instance = super().__new__(cls)
        self.app = PloverPluginApplication(*args)
        return self

    def __init__(self, *args):
        """ The window must be fully initialized before passing to set_window. """
        super().__init__()
        self.app.set_window(self)
        # Hide the menu bar so that the window looks more like a dialog (and can't load dictionaries from disk).
        self.m_menu.setVisible(False)

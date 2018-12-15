from typing import ClassVar

from spectra_lexer.plover.app import PloverPluginApplication
from spectra_lexer.plover.window import PloverPluginWindow


class PloverPlugin(PloverPluginWindow):
    """ Main entry point for Plover plugin. Must be (or appear to be) a subclass of QDialog. """

    # The window and all of its contents are destroyed every time it is closed.
    # The app, engine, and its parts are relatively expensive to create, so a reference is saved
    # in the class dictionary and returned on every call after the first, making it a singleton.
    _app: ClassVar[PloverPluginApplication] = None

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    def __new__(cls, *args):
        """ Initialize the application on the first call; use the saved instance otherwise. """
        if cls._app is None:
            cls._app = PloverPluginApplication(*args)
        return super().__new__(cls)

    def __init__(self, *args):
        """ The window must be fully initialized before passing to set_window. """
        super().__init__()
        self._app.set_window(self)

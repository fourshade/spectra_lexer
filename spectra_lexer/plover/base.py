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

    def __init__(self, *args):
        """ Initialize the application on the first call; use the saved instance otherwise. """
        super().__init__()
        if self._app is None:
            PloverPlugin._app = PloverPluginApplication(*args, window=self)
        # In either case, the application needs the new window instance.
        self._app.new_window(self)

from typing import ClassVar, Type, List

from spectra_lexer.engine import SpectraEngineComponent
from spectra_lexer.gui_qt import SpectraGUIQtBase
from spectra_lexer.plover.interface import PloverPluginInterface
from spectra_lexer.plover.window import PloverWindow

# Default plugin support components. Each must initialize with no arguments.
BASE_PLUGIN_COMPONENTS:List[Type[SpectraEngineComponent]] = [PloverPluginInterface]


class SpectraPloverApplication(SpectraGUIQtBase):

    def __init__(self, *args, **kwargs) -> None:
        """ Initialize the application with base components and keyword arguments from the caller. """
        super().__init__(**kwargs)
        self.engine.connect(*[cmp() for cmp in BASE_PLUGIN_COMPONENTS])
        # Plover currently initializes plugins with only positional arguments,
        # so just pass those along to the interface without looking at them.
        self.engine.send("plover_setup", *args)


class PloverPlugin(PloverWindow):
    """ Main entry point for Plover plugin. Must be (or appear to be) a subclass of QDialog. """

    # The window and all of its contents are destroyed every time it is closed.
    # The app, engine, and its parts are relatively expensive to create, so a reference is saved
    # in the class dictionary and returned on every call after the first, making it a singleton.
    _app: ClassVar[SpectraPloverApplication] = None

    # Docstring is used as tooltip on Plover GUI toolbar, so change it dynamically.
    __doc__ = "See the breakdown of words using steno rules."

    def __init__(self, *args):
        """ Initialize the application on the first call; use the saved instance otherwise. """
        super().__init__()
        if self._app is None:
            PloverPlugin._app = SpectraPloverApplication(*args, window=self)
        # In either case, the application needs the new window instance.
        self._app.new_window(self)

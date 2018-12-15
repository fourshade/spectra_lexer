from spectra_lexer.gui_qt.app import GUIQtApplication
from spectra_lexer.gui_qt.window import BaseWindow
from spectra_lexer.plover.compat import compatibility_check, INCOMPATIBLE_MESSAGE
from spectra_lexer.plover.interface import PloverPluginInterface


class PloverPluginApplication(GUIQtApplication):
    """ Main application class for Plover plugin. """

    is_compatible: bool  # Is the current version requirement for Plover satisfied?

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls, **kwargs)
        # Default plugin component, only created if the application is compatible with the current version of Plover.
        self.is_compatible = compatibility_check()
        if self.is_compatible:
            self.add_children([PloverPluginInterface(*args)])
        return self

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        self.engine_call("plover_load_dicts")

    def set_window(self, window:BaseWindow) -> None:
        """ Connect the window in a separate step. """
        super().set_window(window)
        # If the compatibility check failed, send an error message to the new window.
        if not self.is_compatible:
            self.engine_call("set_status_message", INCOMPATIBLE_MESSAGE)

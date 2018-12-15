from spectra_lexer.gui_qt.app import GUIQtApplication
from spectra_lexer.plover.compat import compatibility_check, INCOMPATIBLE_MESSAGE
from spectra_lexer.plover.interface import PloverPluginInterface


class PloverPluginApplication(GUIQtApplication):
    """ Main application class for Plover plugin. """

    def __init__(self, *components, plover_args, **kwargs):
        # Only initialize the plugin component if Plover is compatible with this version of the program.
        if compatibility_check():
            super().__init__(PloverPluginInterface(*plover_args), *components, **kwargs)
            # After everything else is set up, attempt to load the current Plover dictionaries.
            self.engine_call("plover_load_dicts")
        else:
            super().__init__(*components, **kwargs)
            # If the compatibility check failed, send an error message to the new window.
            self.engine_call("set_status_message", INCOMPATIBLE_MESSAGE)

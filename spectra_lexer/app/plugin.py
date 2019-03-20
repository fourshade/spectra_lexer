import sys

from .gui import GUIQtApplication
from spectra_lexer import plover
from spectra_lexer.utils import dummy


class PloverPluginApplication(GUIQtApplication):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    # Class constants required by Plover for toolbar.
    __doc__ = 'See the breakdown of words using steno rules.'
    TITLE = 'Spectra'
    ICON = ':/spectra_lexer/icon.svg'
    ROLE = 'spectra_dialog'
    SHORTCUT = 'Ctrl+L'

    def __init__(self, *classes):
        """ This component appears as a dialog to interface with Plover in proxy.
            It must translate some attributes into engine call methods and fake others. """
        super().__init__(plover, *classes)
        self.show = lambda *args: self.call("gui_window_show")
        self.close = lambda *args: self.call("gui_window_close")
        # We get our translations from the Plover engine, so auto-loading of translations from disk must be suppressed.
        sys.argv.append("--translations-files=NULL.json")

    def __getattr__(self, attr:str) -> object:
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy

    def run(self, plover_engine=None, *args) -> object:
        """ After everything else is set up, connect the engine and return this proxy to Plover. """
        if plover_engine is None:
            # Plover is not running, so we need to make a fake engine and run some tests with our own event loop.
            self.call("plover_test")
            super().run(*args)
        elif self.call("plover_compatibility_check"):
            # The engine is always the first argument passed by Plover. Others are irrelevant.
            self.call("new_plover_engine", plover_engine)
            self.call("gui_set_enabled", True)
        return self

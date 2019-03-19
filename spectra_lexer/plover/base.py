from .compat import compatibility_check, INCOMPATIBLE_MESSAGE, PloverAction, PloverEngine
from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.utils import dummy


class PloverGUI(GUIQt):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    def __init__(self):
        """ This component appears as a dialog to interface with Plover in proxy.
            It must translate some attributes into engine call methods and fake others. """
        super().__init__()
        self.show = lambda *args: self.engine_call("gui_window_show")
        self.close = lambda *args: self.engine_call("gui_window_close")

    def __getattr__(self, attr:str) -> object:
        """ As a proxy, we fake any attribute we don't want to handle to avoid incompatibility. """
        return dummy

    @on("run")
    def run(self, plover_engine=None, *args) -> object:
        """ After everything else is set up, connect the engine and return this proxy to Plover. """
        if plover_engine is None:
            # Plover is not running, so we need to make a fake engine and run some tests with our own event loop.
            self.engine_call("new_plover_engine", PloverEngine())
            self.engine_call("plover_new_translation", None, [PloverAction()])
            super().run(*args)
        elif not compatibility_check():
            # If the compatibility check fails, don't try to connect to Plover. Send an error.
            self.engine_call("new_status", INCOMPATIBLE_MESSAGE)
        else:
            # The engine is always the first argument passed by Plover. Others are irrelevant.
            self.engine_call("new_plover_engine", plover_engine)
            self.engine_call("gui_set_enabled", True)
        return self

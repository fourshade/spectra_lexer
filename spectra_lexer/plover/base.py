from spectra_lexer.gui_qt import GUIQt
from .compat import compatibility_check, INCOMPATIBLE_MESSAGE, PloverEngine, PloverAction


class PloverGUI(GUIQt):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    GUI_MENUS = ["Tools"]  # The file menu should not be available; clicking "Exit" is likely to crash Plover.

    _plover: PloverEngine = None   # Plover engine. Assumed not to change during run-time.

    @on("setup")
    def get_args(self, options:dict) -> None:
        """ The engine is always the first argument passed by Plover. Others are irrelevant. """
        args = options.get("args")
        if args:
            self._plover = args[0]

    @on("run")
    def run(self) -> object:
        """ After everything else is set up, connect the engine and return the window to Plover. """
        if self._plover is None:
            # Plover is not running, so we need to make a fake engine and run some tests with our own event loop.
            self.engine_call("new_plover_engine", PloverEngine())
            self.engine_call("plover_new_translation", None, [PloverAction()])
            super().run()
        elif not compatibility_check():
            # If the compatibility check fails, don't try to connect to Plover. Send an error.
            self.engine_call("new_status", INCOMPATIBLE_MESSAGE)
        else:
            self.engine_call("new_plover_engine", self._plover)
        # To emulate a dialog, the window must fake a 'finished' signal object with a 'connect' attribute.
        self.window.finished = PuzzleBox()
        return self.window


class PuzzleBox:
    """ The ultimate dummy object. Always. Returns. Itself. """
    def __call__(self, *args, **kwargs): return self
    __getattr__ = __getitem__ = __call__

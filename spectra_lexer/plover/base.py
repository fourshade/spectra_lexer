from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.plover.compat import compatibility_check, INCOMPATIBLE_MESSAGE, PloverEngine, PloverAction


class PloverGUI(GUIQt):
    """ Master component for the Plover plugin; runs on the standard Qt GUI with a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    _plover: PloverEngine = None  # Plover engine. Assumed not to change during run-time.
    _window: MainWindow = None  # Main GUI window. Must be returned to Plover through the main entry point.

    @on("start")
    def start(self, *, plugin_args:tuple=(), **opts) -> None:
        """ Start the GUI with our own window and save the Plover engine reference for later.
            The file menu should not be available; clicking the "Exit" button is likely to crash Plover. """
        self._window = MainWindow()
        # To emulate a dialog, the window must fake a 'finished' signal object with a 'connect' attribute.
        self._window.finished = PuzzleBox()
        super().start(gui_window=self._window, gui_menus=("Tools",), **opts)
        # The engine is always the first argument passed by Plover. Others are irrelevant.
        if plugin_args:
            self._plover = plugin_args[0]

    @respond_to("run")
    def run(self) -> MainWindow:
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
        return self._window


class PuzzleBox:
    """ The ultimate dummy object. Always. Returns. Itself. """
    def __call__(self, *args, **kwargs): return self
    __getattr__ = __getitem__ = __call__

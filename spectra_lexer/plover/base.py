from spectra_lexer.gui_qt import GUIQt
from spectra_lexer.gui_qt.main_window import MainWindow
from spectra_lexer.plover.compat import PloverEngine, PloverAction


class PloverGUI(GUIQt):
    """ The Plover plugin runs on the standard Qt GUI with only a couple (important) differences.
        Notably, the plugin must not create its own QApplication or run its own event loop (unless in test mode). """

    @on("start")
    def start(self, *, gui_menus:tuple=("Tools",), **opts) -> None:
        """ The file menu should not be available; clicking the "Exit" button is likely to crash Plover. """
        super().start(gui_menus=gui_menus, **opts)

    @respond_to("run")
    def run(self) -> MainWindow:
        """ As a plugin, there is already an event loop running somewhere that needs the window we created. """
        # To emulate a dialog, we have to fake a 'finished' signal object with a 'connect' attribute on the window.
        self.window.finished = PuzzleBox()
        return self.window

    @on("plover_test")
    def test(self) -> None:
        """ Plover is not running, so we need to make a fake engine and run some tests with our own event loop. """
        self.engine_call("new_plover_engine", PloverEngine())
        self.engine_call("plover_new_translation", None, [PloverAction()])
        super().run()


class PuzzleBox:
    """ The ultimate dummy object. Always. Returns. Itself. """
    def __call__(self, *args, **kwargs): return self
    __getattr__ = __getitem__ = __call__

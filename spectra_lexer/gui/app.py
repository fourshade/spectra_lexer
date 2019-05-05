from traceback import print_exc

from spectra_lexer import system, steno
from spectra_lexer.core import Application


class GUIApplication(Application):
    """ Abstract starting class for an interactive GUI application. """

    DESCRIPTION = "Run the interactive GUI application by itself."
    CLASS_PATHS = [system, steno]

    def __init__(self):
        """ Let components know the options are done so they can start loading the rest of the GUI. """
        super().__init__()
        self.call("gui_load")

    def run(self) -> int:
        """ Start the GUI event loop and run it indefinitely. Print uncaught exceptions before quitting. """
        try:
            return self.event_loop()
        except Exception:
            print_exc()
            return -1

    def event_loop(self) -> int:
        """ Run an event loop here until the user quits. """
        raise NotImplementedError

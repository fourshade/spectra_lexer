import sys
from traceback import TracebackException

from .main_window import MainWindow
from spectra_lexer import Component


class GUIQtWindow(Component):
    """ GUI Qt operations class for the main window. Starts all other components and handles app-wide events. """

    window: MainWindow = None  # Main GUI window. All GUI activity (including dialogs) is coupled to this window.

    @on("gui_window_load")
    def start(self) -> None:
        """ Make the window, get all required widgets from it, send those to the components, and show it. """
        self.window = MainWindow()
        for group, widgets in self.window.widget_groups().items():
            self.engine_call(f"new_gui_{group}", *widgets)
        self.window.show()

    @on("gui_window_show")
    def show(self) -> None:
        """ If closed, a plugin window should be able to re-open for its host application. """
        if self.window is not None:
            self.window.show()
            self.window.activateWindow()
            self.window.raise_()

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode, but not as a plugin. """
        if self.window is not None:
            self.window.close()

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console and title bar. """
        print(f"SPECTRA: {msg}")
        if self.window is not None:
            self.engine_call("new_title_text", msg)

    @on("new_exception")
    def handle_exception(self, e:Exception) -> bool:
        """ The stack trace for exceptions is displayed in the console and also the main window if loaded.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        if self.window is not None:
            self.engine_call("new_interactive_text", tb_text)
        return True

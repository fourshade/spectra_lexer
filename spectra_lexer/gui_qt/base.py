import sys
from traceback import TracebackException

from PyQt5.QtWidgets import QApplication

from .main_window import MainWindow
from spectra_lexer import Component


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application objects. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)
    window: MainWindow = None  # Main GUI window. Lifecycle determines that of the application.

    @on("start")
    def start(self) -> None:
        """ Make the window, get all required widgets from it, send those to the components, and show it. """
        self.window = MainWindow()
        for group, widgets in self.window.widget_groups().items():
            self.engine_call(f"new_gui_{group}", *widgets)
        self.window.show()
        # Manually process all GUI events at the end to avoid hanging.
        self.QT_APP.processEvents()

    @on("run")
    def run(self) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self.QT_APP.exec_()

    @on("new_status")
    def display_status(self, msg:str) -> None:
        """ Display engine status and general output messages in the console and title bar. """
        print(f"SPECTRA: {msg}")
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

    @on("gui_window_close")
    def close(self) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if self.window is not None:
            self.window.close()

import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component
from spectra_lexer.gui_qt.main_window import MainWindow


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application object. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    _qt_app: QApplication = QApplication.instance() or QApplication(sys.argv)

    @on("start")
    def start(self, *, gui_window:MainWindow=None, gui_menus:tuple=("File", "Tools"), **opts) -> None:
        """ Make the window if necessary, get all required widgets from it, and send them to the components. """
        window = gui_window or MainWindow()
        widgets = window.widgets
        # The menu must be initialized first so it can add items from other components.
        self.engine_call("new_gui_menu", widgets, gui_menus)
        self.engine_call("new_gui_window", widgets)
        self.engine_call("new_menu_item", "File", "Exit", "gui_window_close", window, sep_first=True)
        # Show the window, then manually process all GUI events to avoid hanging.
        window.show()
        self._qt_app.processEvents()

    @respond_to("run")
    def run(self) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self._qt_app.exec_()

    @on("gui_window_close")
    def close(self, window:MainWindow) -> None:
        """ Closing the main window kills the program in standalone mode. Do not call as a plugin. """
        if window is not None:
            window.close()

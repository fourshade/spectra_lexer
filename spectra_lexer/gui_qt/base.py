import sys

from PyQt5.QtWidgets import QApplication

from spectra_lexer import Component


class GUIQt(Component):
    """ Master component for GUI Qt operations. Controls the main window and application objects. """

    # We can create the QApplication at class level since only one is ever allowed to run.
    QT_APP: QApplication = QApplication.instance() or QApplication(sys.argv)

    @on("start")
    def start(self) -> None:
        # Load the window and manually process all GUI events at the end to avoid hanging.
        self.engine_call("gui_window_load")
        self.QT_APP.processEvents()

    @on("run")
    def run(self) -> int:
        """ If no subclasses object, start the GUI event loop and run it indefinitely. """
        return self.QT_APP.exec_()

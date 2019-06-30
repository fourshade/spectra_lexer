from PyQt5.QtWidgets import QMenuBar, QLabel, QLineEdit, QCheckBox

from .widgets import MainWindow, SearchListWidget, StenoBoardWidget, TextGraphWidget, TextTitleWidget
from spectra_lexer.core import Command, Resource
from spectra_lexer.view import VIEW


class GUIQT(VIEW):

    WINDOW: MainWindow = Resource()  # Main GUI window. All GUI activity is coupled to this window.
    W_MENU: QMenuBar = Resource()
    W_BOARD: StenoBoardWidget = Resource()
    W_DESC: QLabel = Resource()
    W_TITLE: TextTitleWidget = Resource()
    W_TEXT: TextGraphWidget = Resource()
    W_INPUT: QLineEdit = Resource()
    W_MATCHES: SearchListWidget = Resource()
    W_MAPPINGS: SearchListWidget = Resource()
    W_STROKES: QCheckBox = Resource()
    W_REGEX: QCheckBox = Resource()

    @Command
    def GUIQTConnect(self) -> None:
        """ Start connecting widgets. """
        raise NotImplementedError

    @Command
    def GUIQTSetEnabled(self, enabled:bool) -> None:
        """ Enable/disable all widgets when GUI-blocking operations are being done. """
        raise NotImplementedError

    @Command
    def GUIQTShowWindow(self) -> None:
        """ For a plugin window, this is called by its host application to re-open it. """
        raise NotImplementedError

    @Command
    def GUIQTCloseWindow(self) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        raise NotImplementedError

    @Command
    def GUIQTUpdate(self, **kwargs) -> None:
        """ Update state attributes and the GUI to match them. """
        raise NotImplementedError

    @Command
    def GUIQTAction(self, action:str) -> None:
        """ Send an action command with the current state. """
        raise NotImplementedError

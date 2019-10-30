from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtWidgets import QMainWindow

from typing import Callable

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar


class _WindowWrapper:
    """ Wrapper class with methods for manipulating the main window. """

    def __init__(self, w_window:QMainWindow) -> None:
        self._w_window = w_window  # Main Qt window.

    def load_icon(self, data:bytes) -> None:
        """ Load the main window icon from a bytes object. """
        im = QPixmap()
        im.loadFromData(data)
        icon = QIcon(im)
        self._w_window.setWindowIcon(icon)

    def show(self) -> None:
        """ Show the window, move it in front of other windows, and activate focus. """
        self._w_window.show()
        self._w_window.activateWindow()
        self._w_window.raise_()

    def close(self) -> None:
        """ Close the main window. """
        self._w_window.close()


class _MenuWrapper:
    """ Wrapper class with methods for populating a menu bar in order. """

    def __init__(self, w_menubar:QMenuBar) -> None:
        self._w_menubar = w_menubar  # Main menu bar widget at the top of the window.
        self._menus = {}             # Contains all menus by heading.

    def add(self, func:Callable[[],None], heading:str, text:str, *, pos:int=None, after_sep:bool=False) -> None:
        """ Create a menu item with label <text> that calls <func> with no args when selected.
            Add it to the menu under <heading> at index <pos>, or at the end if <pos> is None. """
        menu = self._get_menu(heading)
        if after_sep:
            # Add a separator before the next item if <after_sep> is True.
            menu.addSeparator()
        action = QAction(text, menu)
        # Qt signals may provide (useless) args to menu action callbacks. Throw them away in a lambda.
        action.triggered.connect(lambda *ignored: func())
        if pos is not None:
            item_before = menu.actions()[pos]
            menu.insertAction(item_before, action)
        else:
            menu.addAction(action)

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the existing menu with the given heading, or create one if it doesn't exist. """
        menu = self._menus.get(heading)
        if menu is None:
            menu = self._w_menubar.addMenu(heading)
            self._menus[heading] = menu
        return menu

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable the menu bar. """
        self._w_menubar.setEnabled(enabled)


class WindowController:

    def __init__(self, w_window:QMainWindow, w_menubar:QMenuBar) -> None:
        self._window = window = _WindowWrapper(w_window)
        self._menu = menu = _MenuWrapper(w_menubar)
        self.load_icon = window.load_icon
        self.show = window.show
        self.close = window.close
        self.menu_add = menu.add

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable the menu bar. """
        self._menu.set_enabled(enabled)

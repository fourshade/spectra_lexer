from typing import Callable

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar


class SimpleMenu(QMenu):

    def addItem(self, func:Callable[[], None], text:str, *, pos:int=None) -> None:
        """ Create a menu item with label <text> that calls <func> with no args when selected.
            Add it at index <pos>, or at the end if <pos> is None. """
        action = QAction(text, self)
        # Qt signals may provide (useless) args to menu action callbacks. Throw them away in a lambda.
        action.triggered.connect(lambda *ignored: func())
        if pos is not None:
            item_before = self.actions()[pos]
            self.insertAction(item_before, action)
        else:
            self.addAction(action)


class MenuController:

    def __init__(self, w_menubar:QMenuBar) -> None:
        self._w_menubar = w_menubar  # Main menu bar widget at the top of the window.
        self._menus = {}             # Menu sections by heading.

    def get_section(self, heading:str) -> SimpleMenu:
        """ Return the menu with the given heading. Create it and add it to the menu bar if it does not exist. """
        if heading in self._menus:
            return self._menus[heading]
        menu = self._menus[heading] = SimpleMenu(heading)
        self._w_menubar.addMenu(menu)
        return menu

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable the menu bar. """
        self._w_menubar.setEnabled(enabled)

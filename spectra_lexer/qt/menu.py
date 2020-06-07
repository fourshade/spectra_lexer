from typing import Callable

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar


class MenuController:
    """ Wrapper class with methods for populating a menu bar in order. """

    def __init__(self, w_menubar:QMenuBar) -> None:
        self._w_menubar = w_menubar  # Main menu bar widget at the top of the window.
        self._menus = {}             # Contains all menus by heading.

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the existing menu with the given heading, or create one if it doesn't exist. """
        menu = self._menus.get(heading)
        if menu is None:
            menu = self._w_menubar.addMenu(heading)
            self._menus[heading] = menu
        return menu

    def add(self, func:Callable[[], None], heading:str, text:str, *, pos:int=None) -> None:
        """ Create a menu item with label <text> that calls <func> with no args when selected.
            Add it to the menu under <heading> at index <pos>, or at the end if <pos> is None. """
        menu = self._get_menu(heading)
        action = QAction(text, menu)
        # Qt signals may provide (useless) args to menu action callbacks. Throw them away in a lambda.
        action.triggered.connect(lambda *ignored: func())
        if pos is not None:
            item_before = menu.actions()[pos]
            menu.insertAction(item_before, action)
        else:
            menu.addAction(action)

    def add_separator(self, heading:str) -> None:
        """ Add a separator to the end of the menu under <heading>. """
        menu = self._get_menu(heading)
        menu.addSeparator()

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable the menu bar. """
        self._w_menubar.setEnabled(enabled)

from typing import Callable

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar


class MainMenu(QMenuBar):
    """ Main menu class with convenience methods for populating a menu bar in order. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.menus = {}  # Contains all menus by heading.

    def add(self, func:Callable[[],None], heading:str, text:str, *, pos:int=None, after_sep:bool=False) -> None:
        """ Create a menu item with label <text> that calls <func> with no args when selected.
            Add it to the menu under <heading> at index <pos>, or at the end if <pos> is None. """
        m = self._get_menu(heading)
        if after_sep:
            # Add a separator before the next item if <after_sep> is True.
            m.addSeparator()
        action = QAction(text, m)
        if pos is not None:
            before = m.actions()[pos]
            m.insertAction(before, action)
        else:
            m.addAction(action)
        action.triggered.connect(func)

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the existing menu with the given heading, or create one if it doesn't exist. """
        m = self.menus.get(heading)
        if m is None:
            self.menus[heading] = m = self.addMenu(heading)
        return m

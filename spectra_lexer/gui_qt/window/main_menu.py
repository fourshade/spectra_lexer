from typing import Callable

from PyQt5.QtWidgets import QMenu, QMenuBar


class MainMenu(QMenuBar):
    """ Main menu class with convenience methods for populating a menu bar in order. """

    menus: dict  # Contains all menus by heading.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self.menus = {}

    def add(self, func:Callable[[],None], heading:str, text:str, after_sep:bool=False) -> None:
        """ Create a menu item with label <text> that calls <func> with no args when selected.
            Add it to the next open slot in the menu under <heading>. Make that menu if it doesn't exist yet. """
        m = self._get_menu(heading)
        if after_sep:
            # Add a separator before the next item if requested.
            m.addSeparator()
        action = m.addAction(text)
        # Qt may provide (useless) args to menu action callbacks. Throw them away in a lambda.
        action.triggered.connect(lambda *_: func())

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the existing menu with the given heading, or create one if it doesn't exist. """
        m = self.menus.get(heading)
        if m is None:
            self.menus[heading] = m = self.addMenu(heading)
        return m

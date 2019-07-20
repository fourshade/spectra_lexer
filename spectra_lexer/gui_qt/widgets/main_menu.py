from typing import Callable, Dict

from PyQt5.QtWidgets import QMenu, QMenuBar


class MainMenu(QMenuBar):
    """ Main menu class with convenience methods for populating a menu bar in order. """

    _menus: Dict[str, QMenu]  # Tracks all menus created so far by heading.

    def __init__(self, *args):
        super().__init__(*args)
        self._menus = {}

    def add_separator(self, heading:str) -> None:
        """ Add a new separator under the given heading as the next item. """
        m = self._get_menu(heading)
        m.addSeparator()

    def add_item(self, heading:str, text:str, callback:Callable) -> None:
        """ Add a new menu item that calls <callback> when selected. Any args should be ignored. """
        m = self._get_menu(heading)
        m.addAction(text).triggered.connect(lambda *args: callback())

    def _get_menu(self, heading:str) -> QMenu:
        """ Get an existing menu with the given heading, or create it if it doesn't exist. """
        m = self._menus.get(heading)
        if m is None:
            self._menus[heading] = m = self.addMenu(heading)
        return m

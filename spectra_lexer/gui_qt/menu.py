from typing import Callable, Dict

from PyQt5.QtWidgets import QMenu

from spectra_lexer.gui import Menu


class GUIQtMenu(Menu):
    """ GUI Qt extension class for the menu bar. """

    menu_bar = resource("gui:m_menu")  # Menu bar widget.
    headings: Dict[str, QMenu]  # Dict of previously created menu headings.

    def __init__(self):
        super().__init__()
        self.headings = {}

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the menu object corresponding to a heading string, or create a new one. """
        s = self.headings.get(heading)
        if s is None:
            s = self.headings[heading] = self.menu_bar.addMenu(heading)
        return s

    def add_item(self, heading:str, item_text:str, callback:Callable) -> None:
        self._get_menu(heading).addAction(item_text).triggered.connect(callback)

    def add_separator(self, heading:str) -> None:
        self._get_menu(heading).addSeparator()

    def set_enabled(self, enabled:bool) -> None:
        self.menu_bar.setEnabled(enabled)

from typing import Dict

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar, QWidget

from spectra_lexer import on
from spectra_lexer.gui_qt import GUIQtSignalComponent


class GUIQtMenu(GUIQtSignalComponent):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        It is assumed that these operations are only available in standalone mode (not as a plugin).
        Unlike other widgets, this one starts out empty and has items added dynamically on engine start. """

    m_menu: QMenuBar                        # Top-level widget for the entire menu bar.
    menus: Dict[str, QMenu]                 # Menu heading objects (File, Edit, etc.).
    actions: Dict[str, Dict[str, QAction]]  # The items you click.

    def __init__(self, m_menu:QWidget):
        super().__init__()
        self.m_menu = m_menu
        self.menus = {}
        self.actions = {}

    @on("menu_add")
    def add(self, heading:str, action:str, command:str, *args, **kwargs):
        menu_obj = self.menus.get(heading)
        if not menu_obj:
            menu_obj = self.menus[heading] = self.m_menu.addMenu(heading)
            self.actions[heading] = {}
        items = self.actions[heading]
        action_obj = items.get(action)
        if not action_obj:
            action_obj = items[action] = menu_obj.addAction(action)
        # Only call the command with args given on setup. Args passed by the signal are useless.
        def execute(*trash, **garbage):
            return self.engine_send(command, *args, **kwargs)
        action_obj.triggered.connect(execute)

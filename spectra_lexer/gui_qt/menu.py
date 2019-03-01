from typing import Dict, Sequence

from PyQt5.QtWidgets import QAction, QMenu, QMenuBar, QWidget

from spectra_lexer import Component, on


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        Unlike other widgets, this one starts out empty and has items added dynamically on engine configuration. """

    ROLE = "gui_menu"

    m_menu: QMenuBar  # Top-level widget for the entire menu bar.

    _menus: Dict[str, QMenu]                 # Menu headings (File, Edit, etc.) mapped to Qt menu objects.
    _actions: Dict[str, Dict[str, QAction]]  # Dicts with the items you click for each heading.

    def __init__(self):
        super().__init__()
        self._menus = {}
        self._actions = {}

    @on("new_gui_menu")
    def start(self, widgets:Dict[str, QWidget], menus:Sequence[str]=()) -> None:
        """ Get the required widgets and add the initial headings to the menu bar (if any). """
        self.m_menu = widgets["menu"][0]
        self.m_menu.setVisible(bool(menus))
        for m in menus:
            self._menus[m] = self.m_menu.addMenu(m)
            self._actions[m] = {}

    @on("gui_menu_add")
    def add(self, heading:str, action:str, command:str, *args, sep_first:bool=False, **kwargs) -> None:
        """ Add a new menu item under <heading> -> <action> to execute <command>. These are currently permanent.
            Only add the item if its heading exists. Include a separator above the item if <sep_first> is True. """
        menu_obj = self._menus.get(heading)
        if menu_obj is not None:
            if sep_first:
                menu_obj.addSeparator()
            items = self._actions[heading]
            action_obj = items.get(action)
            if not action_obj:
                action_obj = items[action] = menu_obj.addAction(action)
            # Only call the command with args given on setup. Args passed by the signal are useless.
            def execute(*trash, **garbage):
                return self.engine_call(command, *args, **kwargs)
            action_obj.triggered.connect(execute)

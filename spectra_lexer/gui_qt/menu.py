from typing import Dict, Sequence

from PyQt5.QtWidgets import QAction, QMenu, QWidget

from spectra_lexer import Component


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        Unlike other widgets, this one starts out empty and has items added dynamically on engine configuration. """

    _options: list            # Menu items given by components as options at setup.
    _menus: Dict[str, QMenu]  # Menu headings (File, Edit, etc.) mapped to Qt menu objects.

    @on("setup")
    def new_options(self, options:dict) -> None:
        """ Gather the menu items declared as options during setup. """
        self._options = options.get("menu", [])

    @on("new_gui_menu")
    def start(self, widgets:Dict[str, QWidget], menus:Sequence[str]=()) -> None:
        """ Add the initial headings and items to the menu bar. The widget reference does not need to be saved. """
        menu = widgets["menu"][0]
        menu.setVisible(bool(menus))
        self._menus = {m: menu.addMenu(m) for m in menus}
        for opt in self._options:
            args = opt.desc or ()
            self.add(*opt.key.split(":", 1), opt.default, *args)

    @on("new_menu_item")
    def add(self, heading:str, action:str, command:str, *args, menu_pos:int=-1, sep_first:bool=False, **kwargs) -> None:
        """ Add a new menu item under <heading> -> <action> to execute <command>. Only add it if its heading exists. """
        menu_obj = self._menus.get(heading)
        if menu_obj is not None:
            a = QAction(action, menu_obj)
            old_actions = menu_obj.actions()
            if menu_pos < 0 or menu_pos >= len(old_actions):
                # If no position (or an invalid one) was specified, add the new action to the end of the list.
                menu_obj.addAction(a)
            else:
                # If a valid position was specified, add the new action at that index.
                menu_obj.insertAction(old_actions[menu_pos], a)
            # Include a separator above the item if <sep_first> is True.
            if sep_first:
                menu_obj.insertSeparator(a)
            # Only call the command with args given on setup. Args passed by the signal are useless.
            def execute(*trash, **garbage):
                return self.engine_call(command, *args, **kwargs)
            a.triggered.connect(execute)

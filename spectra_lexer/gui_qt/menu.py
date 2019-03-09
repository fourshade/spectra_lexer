from typing import Dict

from PyQt5.QtWidgets import QAction, QMenu, QWidget, QMenuBar

from spectra_lexer import Component


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        Unlike other widgets, this one starts out empty and has items added dynamically on engine configuration. """

    _options: list                 # Menu items given by components as options at setup.
    _menu_bar: QMenuBar            # Menu widget reference.
    _menus: Dict[str, QMenu] = {}  # Menu headings (File, Edit, etc.) mapped to Qt menu objects.

    @on("setup")
    def new_options(self, options:dict) -> None:
        """ Gather the menu items declared as options during setup. """
        self._options = options.get("menu", [])

    @on("new_gui_menu")
    def new_gui(self, menu:QWidget) -> None:
        """ Add the initial headings and items to the menu bar and save the widget reference. """
        self._menu_bar = menu
        args = [[*opt.key.split(":", 1), opt.default] for opt in self._options]
        for a in args:
            self.add(*a)

    @on("new_menu_item")
    def add(self, heading:str, action:str, command:str="", *args, **kwargs) -> None:
        """ Add a new menu item under <heading> -> <action> to execute <command>. Make a new heading if necessary. """
        menu_obj = self._menus.get(heading)
        if menu_obj is None:
            menu_obj = self._menus[heading] = self._menu_bar.addMenu(heading)
        if action == "SEPARATOR":
            # Add a separator on encountering a certain text string. Don't connect it to anything.
            menu_obj.addSeparator()
        else:
            a = QAction(action, menu_obj)
            menu_obj.addAction(a)
            # Only call the command with args given on setup. Args passed by the signal are useless.
            def execute(*trash, **garbage):
                return self.engine_call(command, *args, **kwargs)
            a.triggered.connect(execute)

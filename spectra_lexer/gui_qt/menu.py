from typing import Callable, Dict

from PyQt5.QtWidgets import QAction, QMenu, QWidget, QMenuBar

from spectra_lexer import Component


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        Unlike other widgets, this one starts out empty and has items added dynamically on engine configuration. """

    m_menu: QMenuBar             # Menu widget reference.
    _submenus: Dict[str, QMenu]  # Menu headings (File, Edit, etc.) mapped to Qt sub-menu objects.

    @on("new_gui_menu")
    def new_gui(self, menu:QWidget) -> None:
        """ Save the widget reference. """
        self.m_menu = menu
        self._submenus = {}

    @on("new_menu_item")
    def add_item(self, heading:str, action:str, func:Callable=None) -> None:
        """ Add a new menu item under <heading> -> <action> to execute <func>. """
        menu_obj = self._get_menu(heading)
        a = QAction(action, menu_obj)
        menu_obj.addAction(a)
        if func:
            # Only call the function by itself. Args passed by the signal are useless.
            def execute(*trash, **garbage):
                return func()
            a.triggered.connect(execute)

    @on("new_menu_separator")
    def add_separator(self, heading:str) -> None:
        """ Add a separator to the end of a menu. Don't connect it to anything. """
        self._get_menu(heading).addSeparator()

    def _get_menu(self, heading:str) -> QMenu:
        """ Get the current menu object under <heading>, or make a new one if necessary. """
        if heading not in self._submenus:
            self._submenus[heading] = self.m_menu.addMenu(heading)
        return self._submenus[heading]

from PyQt5.QtWidgets import QMenuBar

from spectra_lexer import Component, on


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu bar item.
        It is assumed that the menu items are only available in standalone mode (not as a plugin).
        Unlike other widgets, this one starts out empty and has items added dynamically on engine configuration. """

    ROLE = "gui_menu"

    m_menu: QMenuBar  # Top-level widget for the entire menu bar.
    menus: dict       # Menu heading objects (File, Edit, etc.).
    actions: dict     # The items you click.

    def __init__(self, m_menu:QMenuBar):
        super().__init__()
        self.m_menu = m_menu
        self.menus = {}
        self.actions = {}

    @on("start")
    def start(self, show_menu=True, **opts) -> None:
        """ Show or hide the menu bar. Is shown by default. """
        self.m_menu.setVisible(show_menu)

    @on("gui_menu_add")
    def add(self, heading:str, action:str, command:str, *args, sep_first:bool=False, **kwargs):
        """ Add a new menu item under <heading> -> <action> to execute <command>. These are currently permanent.
            Create any required headings/items needed, including a separator if <sep_first> is True."""
        menu_obj = self.menus.get(heading)
        if not menu_obj:
            menu_obj = self.menus[heading] = self.m_menu.addMenu(heading)
            self.actions[heading] = {}
        if sep_first:
            menu_obj.addSeparator()
        items = self.actions[heading]
        action_obj = items.get(action)
        if not action_obj:
            action_obj = items[action] = menu_obj.addAction(action)
        # Only call the command with args given on setup. Args passed by the signal are useless.
        def execute(*trash, **garbage):
            return self.engine_call(command, *args, **kwargs)
        action_obj.triggered.connect(execute)

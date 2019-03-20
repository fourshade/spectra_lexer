from spectra_lexer import Component
from spectra_lexer.utils import memoize_one_arg


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu item.
        Unlike other widgets, this one starts out empty and has items added on engine configuration. """

    _items: list  # List of tuples describing menu items. Adding them must wait until the GUI sends the menu widget.

    @on("set_options")
    def new_options(self, *, menu=(), **options) -> None:
        """ Gather the menu items declared as options during setup and prepare the function calls. """
        self._items = [(opt.key.split(":", 1), lambda *xx, args=opt.default: self.engine_call(*args)) for opt in menu]

    @on("new_gui_menu")
    def new_gui(self, menu_bar) -> None:
        """ Add all items to their respective menus. Menus are created and added to the menu bar as needed. """
        get_menu = memoize_one_arg(menu_bar.addMenu)
        for (heading, item_text), func in self._items:
            # Add a new menu item under <heading> -> <item_text> to execute <func>.
            # Add a separator instead if the item text is blank.
            menu = get_menu(heading)
            action = menu.addAction(item_text) if item_text else menu.addSeparator()
            action.triggered.connect(func)

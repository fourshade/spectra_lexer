from spectra_lexer import Component
from spectra_lexer.utils import memoize_one_arg, save_kwargs


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu item.
        Unlike other widgets, this one starts out empty and has items added on engine configuration. """

    menu_bar = Resource("gui", "m_menu", None, "Menu bar.")

    @on("gui_start")
    def gui_start(self, *, menu=(), **options) -> None:
        """ Gather the menu items declared as options during setup and prepare the function calls. """
        items = [(opt.key.split(":", 1), lambda *xx, args=opt.default: self.engine_call(*args)) for opt in menu]
        self._make_menu(items=items)

    @on("gui_opts_done")
    def gui_opts_done(self) -> None:
        self._make_menu(menu_bar=self.menu_bar)

    @save_kwargs
    def _make_menu(self, menu_bar=None, items=None) -> None:
        """ Add all items to their respective menus. Menus are created and added to the menu bar as needed. """
        if items and menu_bar:
            get_menu = memoize_one_arg(menu_bar.addMenu)
            for (heading, item_text), func in items:
                # Add a new menu item under <heading> -> <item_text> to execute <func>.
                # Add a separator instead if the item text is blank.
                menu = get_menu(heading)
                action = menu.addAction(item_text) if item_text else menu.addSeparator()
                action.triggered.connect(func)

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable or disable all menu items when blocking operations are being done. """
        self.menu_bar.setEnabled(enabled)

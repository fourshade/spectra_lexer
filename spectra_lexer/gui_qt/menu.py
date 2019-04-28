from spectra_lexer import Component


class GUIQtMenu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu item.
        Unlike other widgets, this one starts out empty and has items added on engine configuration. """

    menu_bar = resource("gui:m_menu", desc="Menu bar.")

    @on("load_menu")
    def load(self, menu:dict) -> None:
        """ Gather the menu items declared as options during setup and prepare the function calls. """
        # Add all items to their respective menus. Menus are created and added to the menu bar as needed.
        for heading, page in menu.items():
            menu = self.menu_bar.addMenu(heading)
            for item_text, opt in page.items():
                # Add a new menu item under <heading> -> <item_text> to execute <func>.
                # Add a separator instead if the item text starts with "SEP".
                action = menu.addSeparator() if item_text.startswith("SEP") else menu.addAction(item_text)
                action.triggered.connect(lambda *_, args=opt.value: self.engine_call(*args))

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable or disable all menu items when GUI-blocking operations are being done. """
        self.menu_bar.setEnabled(enabled)

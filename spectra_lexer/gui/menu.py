from typing import Callable, Dict

from spectra_lexer.core import Component


class Menu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu item.
        Unlike other components, this one starts out empty and has items added on engine configuration. """

    @on("init:menu")
    def load(self, menu:Dict[str, dict]) -> None:
        """ Add all items to their respective menus. Headings should be added to the menu bar as needed. """
        for heading, page in menu.items():
            for item_text, opt in page.items():
                if item_text.startswith("SEP"):
                    # Add a non-interactive separator if the item text starts with "SEP".
                    self.add_separator(heading)
                else:
                    # Create and connect each item to the engine by calling its returned connector.
                    item_connector = self.add_item(heading, item_text)
                    item_connector(lambda *_, args=opt.value: self.engine_call(*args))

    def add_item(self, heading:str, item_text:str) -> Callable:
        """ Add a new menu item under <heading> -> <item_text> and return an engine connector. """
        raise NotImplementedError

    def add_separator(self, heading:str) -> None:
        """ Add a separator as the next item under <heading>. """
        raise NotImplementedError

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable or disable all menu items when GUI-blocking operations are being done. """
        raise NotImplementedError

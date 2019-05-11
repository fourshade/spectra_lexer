from typing import Callable, Dict

from spectra_lexer.core import Component


class Menu(Component):
    """ GUI operations class for the menu bar. Each action just consists of clicking a menu item.
        Unlike other components, this one starts out empty and has items added on engine configuration. """

    @init("menu")
    def load(self, menu:Dict[str, dict]) -> None:
        """ Add all items to their respective menus. Headings should be added to the menu bar as needed. """
        for heading, page in menu.items():
            for item_text, res in page.items():
                if item_text.startswith("SEP"):
                    # Add a non-interactive separator if the item text starts with "SEP".
                    self.add_separator(heading)
                else:
                    # Create each item and provide a callback for the implementation to connect to the engine.
                    cmds, desc = res.info()
                    def callback(*ignored, args=cmds):
                        return self.engine_call(*args)
                    self.add_item(heading, item_text, callback)

    def add_item(self, heading:str, item_text:str, callback:Callable) -> None:
        """ Add a new menu item under <heading> -> <item_text> that calls <callback> with no args when selected. """
        raise NotImplementedError

    def add_separator(self, heading:str) -> None:
        """ Add a separator as the next item under <heading>. """
        raise NotImplementedError

    @on("gui_set_enabled")
    def set_enabled(self, enabled:bool) -> None:
        """ Enable or disable all menu items (when GUI-blocking operations are being done). """
        raise NotImplementedError

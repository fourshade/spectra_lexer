from functools import partial

from spectra_lexer import Component


class ToolsMenu(Component):
    """ Controller class for a GUI menu. Handles everything except the actual GUI calls. """

    _options: list  # Menu items given by components as options at setup.

    @on("setup")
    def new_options(self, *, menu=(), **options) -> None:
        """ Gather the menu items declared as options during setup. """
        self._options = menu

    @on("start")
    def start(self) -> None:
        """ Add the initial headings and items to the menu bar. """
        for opt in self._options:
            heading, action = opt.key.split(":", 1)
            if action == "SEPARATOR":
                # Add a separator on encountering a certain text string.
                self.engine_call("new_menu_separator", heading)
            else:
                # Make a partial function from the command so the GUI can call it with no args.
                self.engine_call("new_menu_item", heading, action, partial(self.engine_call, *opt.default))

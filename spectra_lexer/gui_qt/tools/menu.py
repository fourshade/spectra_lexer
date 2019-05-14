from ..window import GUI
from spectra_lexer.core import Component, COREApp, CommandClass

# Decorator for a command available as a menu item.
MenuCommand = CommandClass(heading="", text=None)


class QtMenu(Component,
             GUI.Menu,
             COREApp.Start, GUI.Enabled):
    """ GUI Qt implementation class for the menu bar. """

    def on_app_start(self) -> None:
        """ Add new GUI menu items, plus required headers as needed. """
        categories = {}
        for heading, page in MenuCommand.items():
            # See if we have already created a menu with the given heading. If not, create it.
            m = categories.get(heading)
            if m is None:
                m = categories[heading] = self.w_menu.addMenu(heading)
            for text, command in page.items():
                if text is None:
                    # Missing item text designates a separator. Ignore any commands.
                    m.addSeparator()
                else:
                    # Add a new menu item under that calls the unpacked command when selected.
                    def callback(*ignored, cmd=command):
                        return self.engine_call(cmd)
                    m.addAction(text).triggered.connect(callback)

    def on_window_enabled(self, enabled:bool) -> None:
        """ Enable or disable all menu items (when GUI-blocking operations are being done). """
        self.w_menu.setEnabled(enabled)

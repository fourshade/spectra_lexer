from .base import GUIQT
from .tools import MenuCommand


class QtMenu(GUIQT):
    """ GUI Qt implementation class for the menu bar. """

    def GUIQTConnect(self) -> None:
        """ Add new GUI menu items, plus required headers as needed. """
        categories = {}
        for heading, category in MenuCommand.CATEGORIES:
            # See if we have already created a menu with the given heading. If not, create it.
            m = categories.get(heading)
            if m is None:
                m = categories[heading] = self.W_MENU.addMenu(heading)
            # Bind all commands to this component and assign callbacks.
            for text, command, has_sep in category.bind(self):
                if has_sep:
                    m.addSeparator()
                # Add a new menu item that calls the command when selected.
                m.addAction(text).triggered.connect(command)

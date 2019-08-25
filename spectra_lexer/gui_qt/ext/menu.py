from PyQt5.QtWidgets import QMainWindow, QMenuBar

_MENU_ITEMS = []


def MenuItem(heading:str, text:str, *, after_separator:bool=False):
    """ Decorator for methods available as menu items. """
    def capture(fn):
        _MENU_ITEMS.append((heading, text, after_separator, fn))
        return fn
    return capture


class MainMenu(QMenuBar):
    """ Main menu class with convenience methods for populating a menu bar in order. """

    def __init__(self, parent:QMainWindow, bind_to:object):
        """ Add new GUI menu items/separators with required headings as needed. """
        super().__init__(parent)
        menus = {}
        for heading, text, after_sep, fn in _MENU_ITEMS:
            # Get an existing menu with the given heading, or create one if it doesn't exist.
            m = menus.get(heading)
            if m is None:
                menus[heading] = m = self.addMenu(heading)
            # There may be a separator before each item.
            if after_sep:
                m.addSeparator()
            # Bind the method to the given object and add a new menu item that calls it with no args when selected.
            action = m.addAction(text)
            method = fn.__get__(bind_to)
            def menu_action(*ignored, _callback=method) -> None:
                _callback()
            action.triggered.connect(menu_action)
        # For the menu bar to be sized appropriately, this method must be called on the parent.
        parent.setMenuWidget(self)

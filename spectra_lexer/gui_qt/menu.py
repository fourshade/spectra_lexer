from .base import GUIQT
from spectra_lexer.core import Command


class MenuCommand(list):
    """ Decorators for commands available as menu items. """

    CATEGORIES: list = []
    SEP_PREFIX = ":"  # A colon before an item designates a separator.

    def __init__(self, heading:str):
        super().__init__()
        self.CATEGORIES.append((heading, self))

    def __call__(self, key:str):
        """ Capture a single command. """
        def capture(fn):
            cmd = Command(fn)
            self.append((key, cmd))
            return cmd
        return capture

    def after_separator(self, key:str):
        return self(self.SEP_PREFIX + key)

    def bind(self, cmp:object):
        sep = self.SEP_PREFIX
        for key, cmd in self:
            has_sep = False
            if key.startswith(sep):
                key = key[len(sep):]
                has_sep = True
            def call(*ignored, callback=cmd.wrap(cmp)):
                return callback()
            yield key, call, has_sep


class QtMenu(GUIQT):
    """ Qt implementation class for the menu bar. """

    def GUIQTConnect(self) -> None:
        """ Add new GUI menu items, plus required headers as needed. """
        for heading, category in MenuCommand.CATEGORIES:
            m = self.W_MENU.addMenu(heading)
            # Bind all commands to this component and assign callbacks.
            for text, command, has_sep in category.bind(self):
                if has_sep:
                    m.addSeparator()
                # Add a new menu item that calls the command when selected.
                m.addAction(text).triggered.connect(command)

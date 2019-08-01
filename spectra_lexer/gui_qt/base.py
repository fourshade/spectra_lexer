from spectra_lexer.core import Command


class GUIQT:

    @Command
    def GUIQTShowWindow(self) -> None:
        """ For a plugin window, this is called by its host application to re-open it. """
        raise NotImplementedError

    @Command
    def GUIQTCloseWindow(self) -> None:
        """ Closing the main window should kill the program in standalone mode, but not as a plugin. """
        raise NotImplementedError

    @Command
    def GUIQTUpdate(self, **kwargs) -> None:
        """ Update state attributes and the GUI to match them. """
        raise NotImplementedError

    @Command
    def GUIQTAction(self, action:str, **override) -> None:
        """ Send an action command with the current state. Parameters may be temporarily overridden by kwargs. """
        raise NotImplementedError

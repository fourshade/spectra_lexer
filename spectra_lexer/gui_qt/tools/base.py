""" Base module for a Qt dialog framework with callbacks. """

from ..base import GUIQT
from ..menu import MenuCommand

FileMenuCommand = MenuCommand("File")
ToolsMenuCommand = MenuCommand("Tools")
DebugMenuCommand = MenuCommand("Debug")


class GUIQT_TOOL(GUIQT):

    @FileMenuCommand("Load Translations...")
    def TOOLFileOpenTranslations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them (if any). """
        raise NotImplementedError

    @FileMenuCommand("Load Index...")
    def TOOLFileOpenIndex(self) -> None:
        """ Present a dialog for the user to select index files and attempt to load them (if any). """
        raise NotImplementedError

    @FileMenuCommand.after_separator("Close")
    def TOOLFileExit(self) -> None:
        """ Exit the application. """
        raise NotImplementedError

    @ToolsMenuCommand("Edit Configuration...")
    def TOOLConfigOpen(self) -> None:
        """ Create and show the GUI configuration manager dialog. """
        raise NotImplementedError

    @ToolsMenuCommand("Make Index...")
    def TOOLIndexOpen(self) -> None:
        """ Create a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        raise NotImplementedError

    @DebugMenuCommand("Open Console...")
    def TOOLDebugOpen(self) -> None:
        """ Open a new dialog and start the interpreter. """
        raise NotImplementedError

    @DebugMenuCommand("View Object Tree...")
    def TOOLTreeOpen(self) -> None:
        """ Create the tree dialog and all resources using the current components dict. """
        raise NotImplementedError

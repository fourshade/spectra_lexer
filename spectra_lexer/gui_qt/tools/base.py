""" Base module for a Qt dialog framework with callbacks. """

from ..base import GUIQT
from ..menu import MenuCommand

FileMenuCommand = MenuCommand("File")
ToolsMenuCommand = MenuCommand("Tools")
DebugMenuCommand = MenuCommand("Debug")


class GUIQT_TOOL(GUIQT):

    @FileMenuCommand("Load Translations...")
    def file_open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them (if any). """
        raise NotImplementedError

    @FileMenuCommand("Load Index...")
    def file_open_index(self) -> None:
        """ Present a dialog for the user to select index files and attempt to load them (if any). """
        raise NotImplementedError

    @FileMenuCommand.after_separator("Close")
    def file_exit(self) -> None:
        """ Exit the application. """
        raise NotImplementedError

    @ToolsMenuCommand("Edit Configuration...")
    def tools_config_open(self) -> None:
        """ Create and show the GUI configuration manager dialog. """
        raise NotImplementedError

    @ToolsMenuCommand("Make Index...")
    def tools_index_open(self) -> None:
        """ Create a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        raise NotImplementedError

    @DebugMenuCommand("Open Console...")
    def debug_console_open(self) -> None:
        """ Open a new dialog and start the interpreter. """
        raise NotImplementedError

    @DebugMenuCommand("View Object Tree...")
    def debug_tree_open(self) -> None:
        """ Create the tree dialog and all resources using the current components dict. """
        raise NotImplementedError

from typing import Callable, List

from PyQt5.QtWidgets import QFileDialog, QWidget

from .config import ConfigDialog
from .console import ConsoleDialog
from .index import default_index_dialog, SliderIndexDialog
from .objtree import ObjectTreeDialog


class QtDialogFactory:
    """ Factory for GUI menu dialog tools. """

    def __init__(self, parent:QWidget) -> None:
        self._parent = parent  # All GUI dialogs must be children of some widget.

    def open_translations(self) -> List[str]:
        """ Present a dialog for the user to select translation files. """
        return QFileDialog.getOpenFileNames(self._parent, "Load Translations", ".", "JSON Files (*.json)")[0]

    def open_index(self) -> str:
        """ Present a dialog for the user to select an index file. """
        return QFileDialog.getOpenFileName(self._parent, "Load Index", ".", "JSON Files (*.json)")[0]

    def default_index(self, callback:Callable[[int], None]) -> None:
        """ Present a dialog for the user to make a default-sized index and call the callback with the result. """
        callback(default_index_dialog(self._parent))

    def custom_index(self, callback:Callable[[int], None]) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        SliderIndexDialog.new(self._parent, callback=callback)

    def config(self, callback:Callable[[dict], None], *args) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        ConfigDialog.new(self._parent, *args, callback=callback)

    def console(self, *args) -> None:
        """ Create and show the debug console dialog. """
        ConsoleDialog.new(self._parent, *args)

    def objtree(self, *args) -> None:
        """ Create and show the debug tree dialog. """
        ObjectTreeDialog.new(self._parent, *args)

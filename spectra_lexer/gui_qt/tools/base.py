from typing import List

from PyQt5.QtWidgets import QWidget

from .config import ConfigDialog
from .console import ConsoleDialog
from .dialog import ModalDialogGenerator, SingletonDialogGenerator
from .index import IndexSizeDialog, INDEX_STARTUP_MESSAGE
from .objtree import ObjectTreeDialog


class QtDialogTools:
    """ Factory for GUI menu dialog tools. """

    def __init__(self, parent:QWidget) -> None:
        self._modals = ModalDialogGenerator(parent)
        self._singles = SingletonDialogGenerator(parent)

    def open_translations_files(self) -> List[str]:
        """ Present a modal dialog for the user to select translation files. """
        return self._modals.open_files("Load Translations", "json")

    def open_index_file(self) -> str:
        """ Present a modal dialog for the user to select an index file. """
        return self._modals.open_file("Load Index", "json")

    def confirm_startup_index(self) -> bool:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        return self._modals.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE)

    def custom_index(self, *args) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._singles.open_dialog(IndexSizeDialog, *args)

    def config(self, *args) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        self._singles.open_dialog(ConfigDialog, *args)

    def console(self, *args) -> None:
        """ Create and show the debug console dialog. """
        self._singles.open_dialog(ConsoleDialog, *args)

    def objtree(self, *args) -> None:
        """ Create and show the debug tree dialog. """
        self._singles.open_dialog(ObjectTreeDialog, *args)

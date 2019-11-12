from typing import List

from PyQt5.QtWidgets import QWidget

from .config import ConfigDialog
from .console import ConsoleDialog
from .dialog import ModalDialogGenerator, SingletonDialogGenerator
from .index import IndexSizeDialog
from .objtree import ObjectTreeDialog

INDEX_STARTUP_MESSAGE = """<p>
In order to cross-reference examples of specific steno rules, this program must create an index
using your Plover dictionary. The default file size is around 10 MB, and can take anywhere
between 5 seconds and 5 minutes depending on the speed of your machine and hard disk.
Would you like to create one now? You will not be asked again.
</p><p>
(If you cancel, all other features will still work. You can always create the index later from
the Tools menu, and can expand it from the default size as well if it is not sufficient).
</p>"""


class ToolsController:
    """ Factory for GUI menu dialog tools. """

    def __init__(self, parent:QWidget) -> None:
        self._modals = ModalDialogGenerator(parent)
        self._singles = SingletonDialogGenerator(parent)

    def select_translations_files(self) -> List[str]:
        """ Present a modal dialog for the user to select translation files. """
        return self._modals.open_files("Load Translations", "json")

    def select_index_file(self) -> str:
        """ Present a modal dialog for the user to select an index file. """
        return self._modals.open_file("Load Index", "json")

    def confirm_startup_index(self) -> bool:
        """ Present a modal dialog for the user to approve making a default-sized index on first start. """
        return self._modals.yes_or_no("Make Index", INDEX_STARTUP_MESSAGE)

    def open_index_creator(self, *args) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        self._singles.open_dialog(IndexSizeDialog, *args)

    def open_config_editor(self, *args) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        self._singles.open_dialog(ConfigDialog, *args)

    def open_debug_console(self, *args) -> None:
        """ Create and show the debug console dialog. """
        self._singles.open_dialog(ConsoleDialog, *args)

    def open_debug_tree(self, *args) -> None:
        """ Create and show the debug tree dialog. """
        self._singles.open_dialog(ObjectTreeDialog, *args)

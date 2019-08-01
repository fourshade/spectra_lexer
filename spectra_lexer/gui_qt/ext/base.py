""" Base module for a Qt dialog framework with callbacks. """

from .config import ConfigDialog
from .console import ConsoleDialog
from .dialog import DialogContainer, load_files_dialog
from .index import default_index_dialog, SliderIndexDialog
from .objtree import ObjectTreeDialog
from ..view import QtViewManager
from spectra_lexer.resource import RS

_MENU_ITEMS = []


def MenuItem(heading:str, text:str, *, after_separator:bool=False):
    """ Decorator for methods available as menu items. """
    def capture(fn):
        _MENU_ITEMS.append((heading, text, after_separator, fn))
        return fn
    return capture


class QtViewExtended(QtViewManager, RS):
    """ GUI Qt extended operations class with dialog tools. """

    _dialogs: DialogContainer
    _debug_dict: dict = {"NO DATA": "Debug info is missing."}
    _last_config_args: tuple = ()  # Last info arguments received from config component.

    def __init__(self) -> None:
        self._dialogs = DialogContainer()

    def _open(self, dialog_cls:type, *args, **kwargs) -> None:
        self._dialogs.open(dialog_cls, self.window, *args, **kwargs)

    def COREDebug(self, debug_dict:dict) -> None:
        self._debug_dict = debug_dict

    def Load(self) -> None:
        """ Save the window and add new GUI menu items/separators with required headings as needed. """
        super().Load()
        for heading, text, after_sep, fn in _MENU_ITEMS:
            if after_sep:
                self.w_menu.add_separator(heading)
            # Bind the method to this component and add a new menu item that calls it when selected.
            self.w_menu.add_item(heading, text, fn.__get__(self))

    @MenuItem("File", "Load Translations...")
    def FileOpenTranslations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them (if any). """
        self._load_files("translations", ".json")

    @MenuItem("File", "Load Index...")
    def FileOpenIndex(self) -> None:
        """ Present a dialog for the user to select index files and attempt to load them (if any). """
        self._load_files("index", ".json")

    def _load_files(self, res_type:str, *fmts:str) -> None:
        """ Present a modal dialog for <res_type> to select files with an extension in <fmts> for loading.
            Send a command to load the file selection list unless it is empty or the dialog is cancelled. """
        filenames = load_files_dialog(self.window, res_type.title(), *fmts)
        if filenames:
            self.VIEWDialogFileLoad(filenames, res_type)

    @MenuItem("File", "Close", after_separator=True)
    def FileExit(self) -> None:
        """ Exit the application. """
        self.Exit()

    @MenuItem("Tools", "Edit Configuration...")
    def ConfigOpen(self) -> None:
        """ Create and show the GUI configuration manager dialog. """
        self._open(ConfigDialog, self.VIEWConfigUpdate, *self._last_config_args)

    def VIEWConfigInfo(self, *args) -> None:
        self._last_config_args = args

    def RSIndexReady(self, index:dict) -> None:
        """ If there is no index file on first start, present a dialog for the user to make a default-sized index.
            Make the index on accept; otherwise save an empty one so the message doesn't appear again. """
        if not index:
            index_size = default_index_dialog(self.window)
            self._make_index(index_size)

    @MenuItem("Tools", "Make Index...")
    def IndexOpen(self) -> None:
        """ Create a dialog for the index size slider that submits a positive number on accept. """
        self._open(SliderIndexDialog, self._make_index)

    def _make_index(self, index_size:int) -> None:
        """ Disable the GUI while the thread is busy. """
        self.set_enabled(False)
        self.VIEWDialogMakeIndex(index_size)

    def VIEWDialogIndexDone(self, *args) -> None:
        """ Re-enable the GUI once the thread is clear. """
        self.set_enabled(True)

    @MenuItem("Debug", "Open Console...")
    def ConsoleOpen(self) -> None:
        """ Open a new dialog and start the interpreter. """
        self._open(ConsoleDialog, self.COREConsoleInput)
        self.COREConsoleOpen()

    def COREConsoleOutput(self, text_out:str) -> None:
        """ Write console output to the dialog if it exists. Do nothing if there isn't one. """
        console = self._dialogs.get(ConsoleDialog)
        if console is not None:
            console.add_text(text_out)

    @MenuItem("Debug", "View Object Tree...")
    def TreeOpen(self) -> None:
        """ Create the tree dialog using the debug dict as the root namespace. """
        self._open(ObjectTreeDialog, self._debug_dict)

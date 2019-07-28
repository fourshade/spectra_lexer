""" Base module for a Qt dialog framework with callbacks. """

from .config import ConfigDialog
from .console import ConsoleDialog
from .dialog import DialogContainer, load_files_dialog
from .index import default_index_dialog, SliderIndexDialog
from .objtree import ObjectTreeDialog
from ..view import QtViewManager

_MENU_ITEMS = []


def MenuItem(heading:str, text:str, *, after_separator:bool=False):
    """ Decorator for methods available as menu items. """
    def capture(fn):
        _MENU_ITEMS.append((heading, text, after_separator, fn))
        return fn
    return capture


class QtViewExtended(QtViewManager):
    """ GUI Qt extended operations class with dialog tools. """

    _dialogs: DialogContainer
    _components: list                  # Contains every component definition in the application.
    _last_config_args: tuple = ()      # Last info arguments received from config component.
    _last_exception: Exception = None  # Holds last exception caught from the engine.

    def __init__(self) -> None:
        self._dialogs = DialogContainer()
        self._components = [self]

    def _open(self, dialog_cls:type, *args, **kwargs) -> None:
        self._dialogs.open(dialog_cls, self.window, *args, **kwargs)

    def Debug(self, components:list) -> None:
        self._components = components

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

    def VIEWDialogNoIndex(self) -> None:
        """ If there is no index file on first start, present a dialog for the user to make a default-sized index.
            Make the index on accept; otherwise save an empty one so the message doesn't appear again. """
        index_size = default_index_dialog(self.window)
        if index_size:
            self._make_index(index_size)
        else:
            self.VIEWDialogSkipIndex()

    @MenuItem("Tools", "Make Index...")
    def IndexOpen(self) -> None:
        """ Create a dialog for the index size slider that submits a positive number on accept, or 0 on cancel. """
        self._open(SliderIndexDialog, self._make_index)

    def _make_index(self, index_size:int) -> None:
        """ Disable the GUI while the thread is busy. """
        self.GUIQTSetEnabled(False)
        self.VIEWDialogMakeIndex(index_size)

    def VIEWDialogIndexDone(self, *args) -> None:
        """ Re-enable the GUI once the thread is clear. """
        self.GUIQTSetEnabled(True)

    @MenuItem("Debug", "Open Console...")
    def ConsoleOpen(self) -> None:
        """ Open a new dialog and start the interpreter. """
        self._open(ConsoleDialog, self.SYSConsoleInput)
        self.SYSConsoleOpen()

    def SYSConsoleOutput(self, text_out:str) -> None:
        """ Write console output to the dialog if it exists. Do nothing if there isn't one. """
        console = self._dialogs.get(ConsoleDialog)
        if console is not None:
            console.add_text(text_out)

    @MenuItem("Debug", "View Object Tree...")
    def TreeOpen(self) -> None:
        """ Create the tree dialog and add the last engine exception to the resources if any were caught. """
        kwargs = {}
        if self._last_exception is not None:
            kwargs["last_exception"] = self._last_exception
        self._open(ObjectTreeDialog, self._components, **kwargs)

    def HandleException(self, exc:Exception) -> bool:
        """ Save the last exception for introspection. If THAT fails, the system is beyond help. """
        self._last_exception = exc
        return True

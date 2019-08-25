from PyQt5.QtWidgets import QFileDialog, QWidget

from .config import ConfigDialog
from .console import ConsoleDialog
from .index import default_index_dialog, SliderIndexDialog
from .objtree import ObjectTreeDialog
from spectra_lexer.app import StenoApplication
from spectra_lexer.gui_qt.dispatch import AsyncThreadLoader
from spectra_lexer.gui_qt.window import WindowController
from spectra_lexer.steno.analyzer import IndexMapper


class QtDialogLayer:
    """ Handler for GUI menu dialog tools. """

    _parent: QWidget  # All GUI dialogs must be children of the main window.
    _threader: AsyncThreadLoader
    _app: StenoApplication = None
    _debug_vars: dict = None

    def __init__(self, window:WindowController, threader:AsyncThreadLoader) -> None:
        """ Add GUI menu items/separators with protected callbacks as needed. """
        self._parent = window.dialog_parent()
        self._threader = threader
        def menu_add(func, *args, **kwargs) -> None:
            window.menu_add(threader.protect(func), *args, **kwargs)
        menu_add(self.open_translations, "File",  "Load Translations...")
        menu_add(self.open_index,        "File",  "Load Index...")
        menu_add(window.close,           "File",  "Close", after_sep=True)
        menu_add(self.config_editor,     "Tools", "Edit Configuration...")
        menu_add(self.custom_index,      "Tools", "Make Index...")
        menu_add(self.debug_console,     "Debug", "Open Console...")
        menu_add(self.debug_tree,        "Debug", "View Object Tree...")

    def connect(self, app:StenoApplication, debug_vars:dict) -> None:
        """ Save the app and debug vars for dialog use. """
        self._app = app
        self._debug_vars = debug_vars
        # If there is no index file on first start, send up a dialog.
        if app.index_missing:
            self.default_index()

    def open_translations(self) -> None:
        """ Present a dialog for the user to select translation files and attempt to load them all unless cancelled. """
        filenames = QFileDialog.getOpenFileNames(self._parent, "Load Translations", ".", "JSON Files (*.json)")[0]
        if filenames:
            self._threader.run(self._app.load_translations, *filenames, msg_out="Loaded translations from file dialog.")

    def open_index(self) -> None:
        """ Present a dialog for the user to select an index file and attempt to load it unless cancelled. """
        filename = QFileDialog.getOpenFileName(self._parent, "Load Index", ".", "JSON Files (*.json)")[0]
        if filename:
            self._threader.run(self._app.load_index, filename, msg_out="Loaded index from file dialog.")

    def config_editor(self) -> None:
        """ Create and show the GUI configuration manager dialog with info from all active components. """
        dlg = ConfigDialog(self._parent)
        for item in self._app.get_config_info():
            dlg.add_option(item.key, item.value, item.title, item.name, item.description)
        dlg.sig_accept.connect(self._update_config)
        dlg.show()

    def _update_config(self, options:dict) -> None:
        self._threader.run(self._app.set_config, options, msg_out="Configuration saved.")

    def default_index(self) -> None:
        """ If there is no index file on first start, present a dialog for the user to make a default-sized index.
            Make the index on accept; otherwise save an empty one so the message doesn't appear again. """
        choice = default_index_dialog(self._parent)
        self._make_index(choice * IndexMapper.DEFAULT_SIZE)

    def custom_index(self) -> None:
        """ Create and show a dialog for the index size slider that submits a positive number on accept. """
        dlg = SliderIndexDialog(self._parent)
        dlg.setup(IndexMapper.MINIMUM_SIZE, IndexMapper.MAXIMUM_SIZE,
                  IndexMapper.DEFAULT_SIZE, IndexMapper.SIZE_DESCRIPTIONS)
        dlg.sig_accept.connect(self._make_index)
        dlg.show()

    def _make_index(self, size:int) -> None:
        """ Make a custom-sized index and show a success message (if not purposefully empty). """
        msg_out = "Successfully created index!" if size else "Skipped index creation."
        self._threader.run(self._app.make_index, size, msg_in="Making new index...", msg_out=msg_out)

    def debug_console(self) -> None:
        """ Create and show the debug console dialog. """
        dlg = ConsoleDialog(self._parent)
        dlg.setup(self._debug_vars)
        dlg.show()

    def debug_tree(self) -> None:
        """ Create and show the debug tree dialog. """
        dlg = ObjectTreeDialog(self._parent)
        dlg.setup(self._debug_vars)
        dlg.show()

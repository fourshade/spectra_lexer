from functools import partial
from typing import Dict

from PyQt5.QtWidgets import QMainWindow, QDialog

from .config_dialog import ConfigDialog
from .index_dialog import IndexDialog
from .gui_dialog import MessageDialog, FileDialog
from spectra_lexer import Component

# Supported GUI dialog types and whether or not they are modal (i.e. they block input until a value is returned).
_DIALOG_TYPES = {"message": (MessageDialog, True),
                 "file":    (FileDialog,    True),
                 "config":  (ConfigDialog,  False),
                 "index":   (IndexDialog,   False)}


class GUIQtDialogManager(Component):
    """ Creates and manages dialogs from the GUI Qt window. """

    window: QMainWindow = None    # Main window object. Must be the parent of any new dialogs.
    _dialogs: Dict[str, QDialog]  # Dialog object tracker. Each one should persist while visible.

    @on("new_gui_window")
    def new_gui(self, window:QMainWindow) -> None:
        """ Save the main window and start tracking dialogs. """
        self.window = window
        self._dialogs = {}

    @on("new_dialog")
    def dialog(self, k:str, *args) -> None:
        """ Create an instance of GUI dialog type <k> with arguments <*args>, unless one is already visible. """
        if not self._visible_exists(k):
            # The dialog object type is only the last segment of the key. The rest is considered the specific
            # "instance" identifier of the dialog. It is optional; if specified, it will be the first argument in the
            # submit command. This allows different components to handle dialogs of the same type without conflicts.
            *instance, d_type = k.rsplit("-", 1)
            submit_cb = partial(self.engine_call, f"{d_type}_dialog_result", *instance)
            tp, modal = _DIALOG_TYPES[d_type]
            if modal:
                # If the dialog is modal, it will do its job and return a value which goes out as a command.
                submit_cb(tp(self.window, *args))
            else:
                # The new dialog will call a command with its result when accept is clicked. On reject, nothing happens.
                dialog = self._dialogs[k] = tp(self.window, submit_cb, *args)
                dialog.show()

    def _visible_exists(self, k) -> bool:
        """ Return True if a dialog of type <k> is in memory and visible.
            If there's one hiding in memory that has already been closed, destroy it. """
        dialog = self._dialogs.get(k)
        if dialog is not None:
            if dialog.isVisible():
                return True
            dialog.destroy()
        return False

from functools import partial
from typing import Dict, List

from PyQt5.QtWidgets import QMainWindow, QDialog, QFileDialog

from .config_dialog import ConfigDialog
from spectra_lexer import Component


def FileDialog(parent:QFileDialog, title_msg:str, fmts_msg:str, fmts:list) -> List[str]:
    """ Create a modal file open dialog and return multiple file selections in a list.
        If the dialog is cancelled, return an empty list. """
    filter_msg = f"{fmts_msg} (*{' *'.join(fmts)})"
    return QFileDialog.getOpenFileNames(parent, title_msg, ".", filter_msg)[0]


# Supported GUI dialog types and whether or not they are modal (i.e. they block input until a value is returned).
_DIALOG_TYPES = {"file":   (FileDialog,   True),
                 "config": (ConfigDialog, False)}


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
            submit_cb = partial(self.engine_call, f"{k}_dialog_result")
            tp, modal = _DIALOG_TYPES[k]
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

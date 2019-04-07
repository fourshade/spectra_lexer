from functools import partial
from typing import Dict, Sequence

from .config_dialog import ConfigDialog
from .console_dialog import ConsoleDialog
from .dialog import FileDialog, MessageDialog, ToolDialog
from .index_dialog import IndexDialog
from .objtree_dialog import ObjectTreeDialog
from spectra_lexer import Component
from spectra_lexer.utils import str_prefix

DIALOG_TYPES = {"file": FileDialog,
                "message": MessageDialog,
                "config": ConfigDialog,
                "console": ConsoleDialog,
                "index": IndexDialog,
                "objtree": ObjectTreeDialog}


class GUIQtToolDispatcher(Component):
    """ Creates dialogs at the request of tool components and facilitates communications. """

    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    _dialogs: Dict[str, ToolDialog]  # Currently active dialogs.

    def __init__(self):
        self._dialogs = {}

    @on("new_dialog")
    def open(self, d_id:str, command:Sequence, *args) -> None:
        """ Start the dialog specified by type (first part of the id) with the given command and args if not open. """
        if d_id not in self._dialogs:
            # Link the command callback to *this* component's engine and send it as the first argument.
            callback = partial(self.engine_call, *command)
            dtype = str_prefix(d_id, "_")
            retval = DIALOG_TYPES[dtype](self.window, callback, *args)
            # If the dialog was modal, the return value will not be a dialog. It will have done everything; just exit.
            if not isinstance(retval, ToolDialog):
                return
            self._dialogs[d_id] = retval
        # If the dialog already existed or a non-modal one was created, show it.
        self._dialogs[d_id].show()

    @on("new_dialog_message")
    def message(self, d_id:str, *args, **kwargs) -> None:
        """ Send the given args to the chosen dialog if open. """
        dialog = self._dialogs.get(d_id)
        if dialog is not None:
            dialog.receive(*args, **kwargs)

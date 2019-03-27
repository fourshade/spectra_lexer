from .objtree_dialog import ObjectTreeDialog
from spectra_lexer import Component


class ObjectTreeTool(Component):
    """ Component for interactive tree operations. """

    console_menu = Resource("menu", "Debug:View Object Tree...", ["tree_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    dialog: ObjectTreeDialog = None  # Currently active tree dialog window.
    root_vars: dict = {}             # Dict with root variables to load on startup.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the root node's dict with all debug variables. """
        self.root_vars = dvars

    @on("tree_dialog_open")
    def open(self) -> None:
        """ Start the tree with the current root node dict unless already visible. """
        if self.dialog is None:
            self.dialog = ObjectTreeDialog(self.window, None, self.root_vars)
        self.dialog.show()

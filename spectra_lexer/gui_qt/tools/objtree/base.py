import sys

from .collection import ContainerCollection
from .objtree_dialog import ObjectTreeDialog
from spectra_lexer import Component
from spectra_lexer.file import SVG


class ObjectTreeTool(Component):
    """ Component for interactive tree operations. """

    file = Resource("cmdline", "objtree-icons", ":/assets/treeicons.svg", "File with all object tree icons")
    console_menu = Resource("menu", "Debug:View Object Tree...", ["tree_dialog_open"])
    window = Resource("gui", "window", None, "Main window object. Must be the parent of any new dialogs.")

    dialog: ObjectTreeDialog = None  # Currently active tree dialog window.
    root_vars: dict = {}             # Dict with variables to load to the root node on dialog open.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the root vars dict with a tree-based listing of all modules and the debug variables. """
        self.root_vars = {"<modules>": _make_tree(sys.modules), **dvars}

    @on("tree_dialog_open")
    def open(self) -> None:
        """ Start the dialog using the current root vars dict unless already visible. """
        if self.dialog is None:
            # Load the object type icons. On failure, don't use icons.
            icon_dict = SVG.load(self.file, ignore_missing=True)
            root = ContainerCollection(self.root_vars)
            self.dialog = ObjectTreeDialog(self.window, root, icon_dict)
        self.dialog.show()


def _make_tree(src:dict, delim:str=".", root_name:str="__init__") -> dict:
    """ Split all keys in <src> on <delim> and builds a new dict arranged in a hierarchy based on these splits.
        If a key required for a new tree level is occupied, that value will be moved to <root_name>. """
    dest = {}
    for k in sorted(src):
        d = dest
        *first, last = k.split(delim)
        for f in first:
            nd = d.get(f)
            if type(nd) is not dict:
                d[f] = nd = ({} if nd is None else {root_name: nd})
            d = nd
        d[last] = src[k]
    return dest

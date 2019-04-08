import sys

from .collection import ContainerCollection
from spectra_lexer import Component
from spectra_lexer.file import SVG


class ObjectTreeTool(Component):
    """ Component for interactive tree operations. """

    file = Resource("cmdline", "objtree-icons", ":/assets/treeicons.svg", "File with all object tree icons")
    console_menu = Resource("menu", "Debug:View Object Tree...", ["tree_dialog_open"])

    root_vars: dict = {}     # Root variables dict with all debug variables.
    resources: dict = None   # Dict of all resources such as object type icons.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the root object as a tree-based listing of all modules and the debug variables. """
        self.root_vars = {"<modules>": _make_tree(sys.modules), **dvars}

    @on("tree_dialog_open", pipe_to="new_dialog")
    def open(self) -> tuple:
        """ Create the dialog and all resources using the current root vars dict. """
        if self.resources is None:
            # Make a raw root item by making an initial container from a 1-tuple containing the actual root object.
            # Rows of item data are produced upon iterating over the contents. Take the first item from the only row.
            container = ContainerCollection((self.root_vars,))
            root = next(iter(container))[0]
            # Load the SVG icons and other resources. On failure, don't use icons.
            xml_dict = SVG.load(self.file, ignore_missing=True)
            # Each element ID without a starting underline is a valid icon.
            # Aliases for each icon are separated by + characters in the ID.
            icon_ids = {k: k.split("+") for k in xml_dict["id"] if not k.startswith("_")}
            self.resources = {"root_item": root, "xml_bytes": xml_dict["raw"], "icon_ids": icon_ids}
        return "objtree", [""], self.resources


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

import sys
from typing import Callable

from .collection import ContainerCollection
from .info import IconFinder, MroTree, NodeRepr
from spectra_lexer import Component
from spectra_lexer.file import SVG


class ObjectTreeTool(Component):
    """ Component for interactive tree operations. """

    file = Resource("cmdline", "objtree-icons", ":/assets/treeicons.svg", "File with all object tree icons")
    console_menu = Resource("menu", "Debug:View Object Tree...", ["tree_dialog_open"])

    root_vars: dict = {}     # Root node dict with all debug variables.
    resources: dict = None   # Dict of all resources such as object type icons.

    @on("debug_vars")
    def set_debug(self, **dvars) -> None:
        """ Initialize the root object as a tree-based listing of all modules and the debug variables. """
        self.root_vars = {"<modules>": _make_tree(sys.modules), **dvars}

    @on("tree_dialog_open", pipe_to="new_dialog")
    def open(self) -> tuple:
        """ Create the dialog and all resources using the current root vars dict. """
        if self.resources is None:
            # Load the SVG icons and other resources. On failure, don't use icons.
            xml_dict = SVG.load(self.file, ignore_missing=True)
            ifinder = _svg_adapter(xml_dict["raw"], xml_dict["id"])
            self.resources = {"root": ContainerCollection(self.root_vars),
                              "ifinder": ifinder, "tfinder": MroTree(), "vfinder": NodeRepr().repr}
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


def _svg_adapter(xml_string:str, ids:list) -> Callable:
    """ Keeps a set of SVG data and creates an icon finder dict when a GUI renderer becomes available. """
    def create_ifinder(renderer_type:type) -> IconFinder:
        """ Load an icon finder with all icon graphics by ID from an SVG renderer. """
        renderer = renderer_type(xml_string)
        # Each element ID without a starting underline is a valid icon.
        pairs = [(k, renderer(k)) for k in ids if not k.startswith("_")]
        # The types each icon corresponds to are separated by + characters.
        return IconFinder({tp_name: icon for k, icon in pairs for tp_name in k.split("+")})
    return create_ifinder

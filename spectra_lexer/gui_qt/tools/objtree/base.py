from pkgutil import get_data
import sys

from .collection import ContainerCollection
from .impl import ObjectTreeDialog
from ..base import GUIQT_TOOL
from ..dialog import DialogContainer
from spectra_lexer.types.codec import SVGElement

_ICON_DATA = get_data(__package__, "/treeicons.svg")  # File with all object tree icons.


class ObjectTree(GUIQT_TOOL):

    _resources: dict = None  # Dict of all resources such as object type icons.

    class package(dict):
        """ Class for packaging objects and modules under string keys in a nested dict. """
        __slots__ = ()

    def generate_resources(self) -> None:
        icons = {}
        self._resources = {"root_item": self._root_item(), "icons": icons}
        # Decode the SVG icons.
        svg_tree = SVGElement.decode(_ICON_DATA)
        # Elements with at least one type alias are valid icons. Encode a new SVG byte string for each one.
        for elem in svg_tree.iter():
            types = elem.get("spectra_types")
            if types:
                icons[types] = svg_tree.encode_with_defs(elem)

    def _root_item(self) -> dict:
        """ Make a root dict with packages containing all modules and the first level of components. """
        root_dict = self._components_by_path()
        root_dict["modules"] = self._nest(sys.modules)
        # Make a raw root item by making an initial container from a 1-tuple containing this dict.
        container = ContainerCollection((root_dict,))
        # Rows of item data are produced upon iterating over the contents. Take the first item from the only row.
        return next(iter(container))[0]

    def _components_by_path(self) -> dict:
        """ Return a nested dict with each component indexed by its class's module path. """
        d = {}
        for cmp in self.ALL_COMPONENTS:
            ks = type(cmp).__module__.split(".")
            if ks[-1] == "base":
                ks.pop()
            d[".".join(ks[1:])] = cmp
        return self._nest(d)

    def _nest(self, d:dict, pkg_cls:type=package, delim:str=".", root_key:str="__init__") -> dict:
        """ Split all keys on <delim> and nest package dicts in a hierarchy based on these splits.
            If one key is a prefix of another, it may occupy a slot needed for another level of dicts.
            If this happens, move the value one level deeper under <root_key>. """
        pkg = pkg_cls()
        for k, v in d.items():
            d = pkg
            *first, last = k.split(delim)
            for i in first:
                if i not in d:
                    d[i] = pkg_cls()
                elif not isinstance(d[i], pkg_cls):
                    d[i] = pkg_cls({root_key: d[i]})
                d = d[i]
            if last not in d or not isinstance(d[last], pkg_cls):
                d[last] = v
            else:
                d[last][root_key] = v
        return pkg


class ObjectTreeTool(ObjectTree):
    """ Component for interactive tree operations. """

    _dialog: DialogContainer

    def __init__(self) -> None:
        self._dialog = DialogContainer(ObjectTreeDialog)

    def debug_tree_open(self) -> None:
        if self._resources is None:
            self.generate_resources()
        self._dialog.open(self.WINDOW, self._resources)

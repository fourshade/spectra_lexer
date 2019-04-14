from .collection import ContainerCollection
from spectra_lexer import Component
from spectra_lexer.file import SVG


class ObjectTreeTool(Component):
    """ Component for interactive tree operations. """

    file = Resource("cmdline", "objtree-icons", ":/assets/treeicons.svg", "File with all object tree icons")
    m_tree = Resource("menu", "Debug:View Object Tree...", ["tree_dialog_open"])
    debug_vars = Resource("dict", "debug", {})  # Root variables to load on dialog open.

    resources: dict = None   # Dict of all resources such as object type icons.

    @on("tree_dialog_open", pipe_to="new_dialog")
    def open(self) -> tuple:
        """ Create the dialog and all resources using the current root vars dict. """
        if self.resources is None:
            # Make a raw root item by making an initial container from a 1-tuple containing the actual root object.
            # Rows of item data are produced upon iterating over the contents. Take the first item from the only row.
            container = ContainerCollection((self.debug_vars,))
            root = next(iter(container))[0]
            # Load the SVG icons and other resources. On failure, don't use icons.
            xml_dict = SVG.load(self.file, ignore_missing=True)
            # Each element ID without a starting underline is a valid icon.
            # Aliases for each icon are separated by + characters in the ID.
            icon_ids = {k: k.split("+") for k in xml_dict["id"] if not k.startswith("_")}
            self.resources = {"root_item": root, "xml_bytes": xml_dict["raw"], "icon_ids": icon_ids}
        return "objtree", [""], self.resources

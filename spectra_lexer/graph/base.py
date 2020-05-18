from typing import Container, List, Sequence, Tuple


class IBody:

    __slots__ = ()

    def height(self) -> int:
        """ Return the height of the node body in rows. """
        raise NotImplementedError

    def width(self) -> int:
        """ Return the width of the node body in columns. """
        raise NotImplementedError

    def is_always_bold(self) -> bool:
        raise NotImplementedError

    def is_separator(self) -> bool:
        raise NotImplementedError

    def text(self, col:int) -> Tuple[int, str]:
        """ Return a column offset (possibly shifted) with a string of text to start writing there as a row. """
        raise NotImplementedError


class IConnectors:
    """ A set of connector characters joining a node to its parent. """

    __slots__ = ()

    def strlist(self, height:int) -> List[str]:
        """ Return a list of strings where index 0 goes under the parent, then extends to <height>. """
        raise NotImplementedError

    def min_height(self) -> int:
        """ Minimum height is 3 characters, or 2 if the bottom attachment is one character wide. """
        raise NotImplementedError


class LayoutNode:
    """ Abstract node in a tree structure of steno rules. Each node may have zero or more children. """

    def children(self) -> Sequence["LayoutNode"]:
        """ Return all direct children of this node. """
        raise NotImplementedError

    def min_row(self) -> int:
        """ Return the minimum row index to place the top of the node body relative to the parent. """
        raise NotImplementedError

    def start_col(self) -> int:
        """ Return the column index to place the left side of the node body relative to the parent.
            This is also the relative start column index to highlight when this node is selected. """
        raise NotImplementedError

    def min_height(self) -> int:
        """ Return the minimum height of the node in rows. """
        raise NotImplementedError

    def min_width(self) -> int:
        """ Return the minimum width of the node in columns. """
        raise NotImplementedError

    def is_separator(self) -> bool:
        raise NotImplementedError


class GraphLayout:
    """ Recursive tree of usable graph layout items. """

    def __init__(self, node:LayoutNode, top:int, left:int, bottom:int, right:int, sublayouts:Sequence["GraphLayout"]):
        self.node = node
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right
        self.sublayouts = sublayouts  # Sublayouts in the order they should be drawn.


class TextElement:
    """ A single text element with markup. Corresponds to exactly one printed character. """

    __slots__ = ["char", "ref", "color_index", "bold_at", "activators"]

    def __init__(self, char:str, ref="", color_index=0, bold_at=10, activators:Container[str]=()) -> None:
        self.char = char                # Printed text character.
        self.ref = ref                  # Primary ref string - links to the node that was responsible for this element.
        self.color_index = color_index  # Numerical index to a table of RGB colors.
        self.bold_at = bold_at          # 0 = always bold, 1 = bold when activated, >1 = never bold.
        self.activators = activators    # Contains all refs that will activate (highlight) this element.


TextElementGrid = Sequence[Sequence[TextElement]]  # Abstract 2D grid of text elements.

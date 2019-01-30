""" Module for higher-level text objects such as nodes, containers, and connectors. """

from typing import List, Tuple

from spectra_lexer.graph.text.layout.primitive import *
from spectra_lexer.utils import nop


class Object(Primitive, List[Tuple[int, int, Primitive]]):
    """ A text object is an ordered composite of text primitives with offsets in the form (row, col, item). """

    def add(self, item:Primitive=None, row:int=0, col:int=0) -> None:
        """ Add a text object with a specific offset from this container's origin.
            Maintain the container's width and height as the maximum extent of any of its children. """
        if item is None:
            return
        self.append((row, col, item))
        new_h = row + item.height
        if new_h > self.height:
            self.height = new_h
        new_w = col + item.width
        if new_w > self.width:
            self.width = new_w

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw all primitives in order with their offsets. """
        for (r, c, obj) in self:
            obj.write(canvas, row + r, col + c)


class ObjectNode(Object):
    """ Grid of text lines that form a node and its attachments one character in each direction.
        Sections of text belonging to a single node are added with positions depending on the node attributes. """

    TEXT = PrimitiveBody               # Primitive constructor for the text itself.
    BOTTOM = PrimitiveContainerBottom  # Primitive constructor for the section above the text.
    TOP = PrimitiveContainerTop        # Primitive constructor for the section below the text.
    CONNECTOR = PrimitiveConnector     # Primitive constructor for vertical connectors.
    ENDPIECE = PrimitiveEndpiece       # Primitive constructor for extension connectors.

    def __init__(self, s="", tag=None) -> None:
        """ Add a new line with the node's text starting at the origin. """
        super().__init__()
        self.tag = tag
        self.add(self.TEXT(s, tag))

    def attach(self, parent:Object, row:int, col:int) -> None:
        """ Attach <self> to its parent object at offset (row, col). """
        parent.add(self, row, col)

    def draw_connectors(self, parent:Object, p_col:int, p_len:int, c_row:int, c_col:int, c_len:int) -> None:
        """ Add connectors to <parent> using properties and coordinates of a child <self>.
            <c_row> is the row index occupied by the child. The parent is by definition at row index 0.
            <p_col> and <c_col> are the left column indices. For now, they should always be the same.
            <p_len> and <c_len> are the lengths of the attachment containers in columns. """
        tag = self.tag
        w = parent.width
        # Add a bottom container ├--┐ near the child.
        parent.add(self.BOTTOM(c_len, tag), c_row - 1, c_col)
        # If the top container would be left off the end, we need an extension and an endpiece ┐ instead.
        if p_len == 0 and p_col >= w:
            parent.add(self.CONNECTOR(1, tag), 1, p_col)
            parent.add(self.ENDPIECE(w - p_col + 1, tag), 0, p_col)
        else:
            # Add a top container ├--┘ near the parent.
            parent.add(self.TOP(p_len, tag), 1, p_col)
        # If there's room, add a connector between the containers.
        if c_row > 3:
            parent.add(self.CONNECTOR(c_row - 3, tag), 2, c_col)


class ObjectNodeInversion(ObjectNode):
    """ Graphical element for a standard node whose rule describes an inversion of steno order. """

    BOTTOM = PrimitiveContainerInversion


class ObjectSeparators(ObjectNode):
    """ A row of stroke separators. These are not connected to anything, nor is their ownership displayed. """

    TEXT = PrimitiveSeparator

    def draw_connectors(self, parent:Object, p_col:int, p_len:int, c_row:int, c_col:int, c_len:int) -> None:
        pass


class ObjectNodeUnmatched(ObjectNode):
    """ Graphical element for unmatched keys. """

    BOTTOM = TOP = PrimitiveContainerUnmatchedMid
    CONNECTOR = nop

    def draw_connectors(self, parent:Object, p_col:int, p_len:int, c_row:int, c_col:int, c_len:int) -> None:
        """ Connect two nodes together with a gap ending in question marks on both sides. """
        super().draw_connectors(parent, p_col, p_len, c_row, c_col, c_len)
        for r in range(2, c_row - 4):
            parent.add(PrimitiveContainerUnmatchedMid(p_len, self.tag), r, c_col)
        parent.add(PrimitiveContainerUnmatchedEnd(p_len, self.tag), c_row - 4, c_col)
        parent.add(PrimitiveContainerUnmatchedEnd(c_len, self.tag), c_row - 2, c_col)

""" Module for higher-level text objects such as nodes, containers, and connectors. """

from typing import List, Tuple

from spectra_lexer.interactive.graph.text.generator.canvas import Canvas
from spectra_lexer.interactive.graph.text.generator.pattern import Pattern
from spectra_lexer.interactive.graph.text.generator.primitive import Primitive


class Object(Primitive, List[Tuple[int, int, Primitive]]):
    """ A text object is an ordered composite of text primitives with offsets in the form (row, col, item). """

    height = width = 0  # Empty objects take up no space.

    def add(self, item:Primitive, row:int=0, col:int=0) -> None:
        """ Add a text object with a specific offset from this container's origin.
            Maintain the container's width and height as the maximum extent of any of its children. """
        self.append((row, col, item))
        new_h = row + item.height
        if new_h > self.height:
            self.height = new_h
        new_w = col + item.width
        if new_w > self.width:
            self.width = new_w

    def render(self, row:int=0, col:int=0) -> Tuple[list, list]:
        """ Render all text objects onto a grid of the minimum required size. Try again with a larger one if it fails.
            Return a list of standard strings and a grid with node references indexed by position. """
        s = row + col
        canvas = Canvas.blanks(self.height + s, self.width + s)
        try:
            self.write(canvas, row, col)
        except ValueError:
            return self.render(row + bool(s), col + (not s))
        return canvas.compile_strings(), canvas.compile_tags()

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw all primitives in order with their offsets. """
        for (r, c, obj) in self:
            obj.write(canvas, row + r, col + c)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {list(self)!r}>"


class ObjectNode(Object):
    """ Grid of text lines that form a node and its attachments one character in each direction.
        Sections of text belonging to a single node are added with positions depending on the node attributes. """

    pattern: Pattern  # Structure with symbol pattern templates for connectors and containers.

    def __init__(self, s:str, tag:object, pattern:Pattern) -> None:
        """ Add the first primitive: a new line with the node's text starting at the origin. """
        self.tag = tag
        self.pattern = pattern
        if pattern.TEXT is not None:
            self.add(pattern.TEXT(s, tag))

    def attach(self, parent:Object, row:int, col:int) -> None:
        """ Attach <self> to its parent object at offset (row, col). """
        parent.add(self, row, col)

    def draw_connectors(self, parent:Object, p_col:int, p_len:int, c_row:int, c_col:int, c_len:int) -> None:
        """ Add connectors to <parent> using properties and coordinates of a child <self>.
            <c_row> is the row index occupied by the child. The parent is by definition at row index 0.
            <p_col> and <c_col> are the left column indices. For now, they should always be the same.
            <p_len> and <c_len> are the lengths of the attachment containers in columns. """
        w = parent[0][2].width
        # If there's more than one space available, add a bottom container ├--┐ near the child.
        if c_row > 2:
            self.add_symbols_to(parent, self.pattern.BOTTOM, c_len, c_row - 1, c_col)
        # Add a top container ├--┘ near the parent. We always need this at minimum even with zero attach length.
        self.add_symbols_to(parent, self.pattern.TOP, p_len or 1, 1, p_col)
        # If the top container runs off the end, we need a corner ┐ endpiece.
        if p_col >= w:
            self.add_symbols_to(parent, self.pattern.ENDPIECE, w - p_col + 1, 0, p_col)
        # If there's a gap, add a connector between the containers.
        if c_row > 3:
            self.add_symbols_to(parent, self.pattern.CONNECTOR, c_row - 3, 2, c_col)

    def add_symbols_to(self, obj:Object, pattern_cls:type, length:int, row:int=0, col:int=0) -> None:
        """ Create a new primitive from <pattern_cls> with our tag and add it to <obj> at offset (row, col). """
        if pattern_cls is not None:
            obj.add(pattern_cls(length, self.tag), row, col)


class ObjectNodeUnmatched(ObjectNode):
    """ Graphical element for unmatched keys. These have broken connectors ending in question marks on both sides. """

    def __init__(self, s:str, tag:object, pattern:Pattern) -> None:
        """ Add the body with an extra row offset to ensure that empty matches have enough space. """
        self.tag = tag
        self.pattern = pattern
        if pattern.TEXT is not None:
            self.add(pattern.TEXT(s, tag), 3)

    def draw_connectors(self, parent:Object, p_col:int, p_len:int, c_row:int, c_col:int, c_len:int) -> None:
        """ Draw top connectors downward and end in question marks just before reaching the bottom. """
        super().draw_connectors(parent, p_col, p_len, c_row, c_col, c_len)
        for r in range(2, c_row - 1):
            self.add_symbols_to(parent, self.pattern.TOP, p_len, r, c_col)
        self.add_symbols_to(parent, self.pattern.CUSTOM, p_len, c_row - 1, c_col)
        self.add_symbols_to(parent, self.pattern.CUSTOM, c_len, c_row + 1, c_col)
        self.add_symbols_to(parent, self.pattern.TOP, c_len, c_row + 2, c_col)

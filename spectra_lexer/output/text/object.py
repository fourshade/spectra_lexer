""" Module for abstract text objects. The intermediate layer between raw tagged strings and specific graphics. """

from operator import methodcaller
from typing import Iterable, List

from spectra_lexer.output.text.string import TaggedGrid


class TextObject:
    """ An abstract object whose only job is to write text to a canvas. Each one may be "owned" by a node. """

    col: int  # Offset X in characters moving right from the origin.
    row: int  # Offset Y in characters moving down from the origin.

    def __init__(self, row:int=0, col:int=0):
        self.row = row
        self.col = col

    def bounds(self):
        """ Return the maximum X and Y bounds the object could occupy. By default it takes up one character. """
        return self.row + 1, self.col + 1

    def order(self):
        """ Default ordering key is 0. Most objects will not deviate from this. """
        return 0

    def write(self, canvas:TaggedGrid) -> None:
        """ Draw the object on the text canvas. By default it draws a test character at the offset. """
        canvas.write_row("X", self.row, self.col)


class TextGrid(TextObject, TaggedGrid):
    """ List of output text structures that form a full 2D text graph when concatenated with newlines
        as well as a grid with additional info about node locations for highlighting support. """

    def bounds(self):
        """ Return each offset plus the size of the grid in that dimension. """
        rows, cols = self.size()
        return self.row + rows, self.col + cols

    def write(self, canvas:TaggedGrid) -> None:
        """ Draw the text grid on the canvas. They are the same type, so a direct memory copy is possible. """
        canvas.memcpy(self, self.row, self.col)


class TextObjectCollection(TextObject, List[TextObject]):
    """ An aggregate of text objects. Each is drawn at the aggregate's offset in addition to their own.
        Recursive collections of collections are allowed, but ill-advised because of performance issues. """

    def bounds(self) -> Iterable[int]:
        """ Return the maximum X and Y bounds out of any member objects. """
        return map(max, zip(*[obj.bounds() for obj in self]))

    def write(self, canvas:TaggedGrid) -> None:
        """ Sort all text objects by order and render them. Objects that are tied should stay in relative order. """
        for obj in sorted(self, key=methodcaller("order")):
            obj.write(canvas)

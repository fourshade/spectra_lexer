""" Module for abstract text objects. The intermediate layer between raw tagged strings and specific graphics. """

from operator import attrgetter
from typing import List, Sequence

from spectra_lexer.output.text.grid import TaggedGrid


class TextObject:
    """ An abstract object whose job is to write text to a canvas with optional sort ordering.
        Each occupies a bounded rectangle. <offset> and <bounds> are the top-left and bottom-right corners. """

    # Default ordering key is 0. Most objects will not deviate from this.
    ORDER = 0

    offset: tuple = (0, 0)  # Starting offset (toprow, leftcol) in characters.
    size: tuple = (1, 1)    # Size (height, width) of maximum rectangular extent.

    def __init__(self, row:int=None, col:int=0, height:int=None, width:int=1):
        """ By default, the rectangle starts at the origin and extends 1 unit down and to the right.
            Some subclasses may declare <size> to be a property. Do not attempt to set it unless given args. """
        if row is not None:
            self.offset = row, col
            if height is not None:
                self.size = height, width

    def __contains__(self, cpos:tuple) -> bool:
        """ Return True if the character at <cpos> = (row, col) is contained within this object. """
        top, left = self.offset
        h, w = self.size
        row, col = cpos
        return top <= row < top + h and left <= col < left + w

    def write(self, canvas:TaggedGrid, row:int=0, col:int=0) -> None:
        """ Draw the object on the text canvas. By default it fills a rectangle of test characters at the offset. """
        y, x = self.offset
        h, w = self.size
        canvas.write(["X" * w] * h, None, row + y, col + x)


class TextGrid(TextObject):
    """ A text object with a basic grid of text lines of the same type as the main drawing canvas. """

    grid: TaggedGrid  # Character grid to prepare before actual writing.

    def __init__(self, row:int, col:int, row_count:int=0, col_count:int=0) -> None:
        """ Create a blank grid ready for drawing with the given size. """
        super().__init__(row, col, row_count, col_count)
        self.grid = TaggedGrid.blanks(row_count, col_count)

    def write(self, canvas:TaggedGrid, row:int=0, col:int=0) -> None:
        """ Draw the text grid on the canvas. They are the same type, so a direct memory copy is possible. """
        y, x = self.offset
        canvas.memcpy(self.grid, row + y, col + x)


class TextObjectCollection(TextObject):
    """ An aggregate of text objects. Each is drawn at the aggregate's offset in addition to their own. """

    _display_list: List[TextObject]

    def __init__(self, row:int=0, col:int=0, objects:Sequence[TextObject]=()):
        """ Make a list of every text object to display. May include others of this type recursively. """
        super().__init__(row, col)
        self._display_list = list(objects)
        # Unpack any objects that are themselves collections to eliminate unnecessary recursion.
        # Add our global offset to each object and compute a size that covers the maximum bounds of all child objects.
        bounds_h, bounds_w = [], []
        for obj in objects:
            objrow, objcol = obj.offset
            h, w = obj.size
            bounds_h.append(objrow + h)
            bounds_w.append(objcol + w)
        self.size = max(bounds_h), max(bounds_w)

    def write(self, canvas:TaggedGrid, row:int=0, col:int=0) -> None:
        """ Sort all text objects by order and draw them. Objects that are tied should stay in relative order. """
        self._display_list.sort(key=attrgetter("ORDER"))
        y, x = self.offset
        for obj in self._display_list:
            obj.write(canvas, row + y, col + x)

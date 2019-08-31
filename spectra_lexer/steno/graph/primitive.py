""" Module for primitive operations consisting of drawing lines and columns of text. """

from functools import lru_cache
from typing import Callable, Sequence

from .canvas import Canvas


class BasePrimitive:
    """ Abstract object to write text to a canvas. Defines only a maximum rectangle size. """

    height: int = 1  # Total height in rows.
    width: int = 1   # Total width in columns.

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the object on <canvas> with an offset of <row, col>. """
        raise NotImplementedError

    def __str__(self) -> str:
        """ Return the rendered text grid followed by a grid of numbers representing each distinct node tag. """
        canvas = Canvas.blanks(self.height + 2, self.width + 2)
        self.write(canvas, 1, 1)
        lines = canvas.compile_strings()
        tags = canvas.compile_tags()
        unique_tags = {t for line in tags for t in line if t is not None}
        tag_chars = {t: chr(i) for i, t in enumerate(unique_tags, ord('0'))}
        tag_chars[None] = ' '
        for line, t in zip(lines, tags):
            line += map(tag_chars.get, t)
        return "\n".join(map("".join, lines))

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}:\n\n{self}>'


class PrimitiveRow(BasePrimitive):
    """ Writes a text string to a row of a canvas under a single node tag. """

    def __init__(self, s:str, tag:object) -> None:
        """ The row starts at the origin and extends to the right. """
        self.text = s   # String to draw.
        self.tag = tag  # Identifier for the node.
        self.width = len(s)

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the string on the text canvas starting at the upper-left going right. """
        canvas.write_row(self.text, self.tag, row, col)


class PrimitiveColumn(BasePrimitive):
    """ Writes a text string to a column of a canvas under a single node tag. """

    def __init__(self, s:str, tag:object) -> None:
        """ The column starts at the origin and extends down. """
        self.text = s   # String to draw.
        self.tag = tag  # Identifier for the node.
        self.height = len(s)

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the string on the text canvas starting at the upper-left going down. """
        canvas.write_column(self.text, self.tag, row, col)


class PrimitiveRowReplace(BasePrimitive):
    """ Replaces every space in a canvas row with a given character. """

    width = 0  # Row substitution operations should advance one row, but no columns.

    def __init__(self, c:str, tag:object) -> None:
        self.text = c   # Character to draw.
        self.tag = tag  # Identifier for the node.

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Replace every space in the row with unowned copies of the character. """
        canvas.row_replace(row, " ", self.text)


class Composite(list, BasePrimitive):
    """ An ordered composite of text primitives with offsets in the form (row, col, item). """

    height = width = 0  # Empty containers take up no space.

    def add(self, item:BasePrimitive, row:int=0, col:int=0) -> None:
        """ Add a text object with a specific offset from this container's origin.
            Maintain the container's width and height as the maximum extent of any of its children. """
        self.append((item, row, col))
        new_h = row + item.height
        if new_h > self.height:
            self.height = new_h
        new_w = col + item.width
        if new_w > self.width:
            self.width = new_w

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw all primitives in order with their offsets. """
        for (item, r, c) in self:
            item.write(canvas, row + r, col + c)


def _pattern_generator(prim_cls:type) -> Callable:
    """ Create primitives to write a pattern with a given length to a canvas.
        The output of this generator goes in a class; the tag will be the object that called it. """
    def primitive_generator(single:str, pattern:str=None) -> Callable:
        """ Return a memoized constructor for a variable-length pattern based on a specific character set.
            Each pattern consists of a line of repeated characters with the first and last characters being unique.
            single - A single character used when (and only when) the pattern is length 1.
            pattern - A sequence of 3 characters. If None, the single character fills in for all three:
                first - Starting character for all patterns with length > 1.
                middle - A character repeated to fill the rest of the space in all patterns with length > 2.
                last - Ending character for all patterns with length > 1. """
        first, middle, last = (pattern or single * 3)
        @lru_cache(maxsize=None)
        def constructor(length:int) -> str:
            """ Return a pattern string with unique ends based on a set of construction symbols and a length. """
            if length < 2:
                return single
            return first + middle * (length - 2) + last
        def make_primitive(self, length:int) -> BasePrimitive:
            return prim_cls(constructor(length), self)
        return make_primitive
    return primitive_generator


PatternRow = _pattern_generator(PrimitiveRow)
PatternColumn = _pattern_generator(PrimitiveColumn)


class ClipMatrix:
    """ Provides integer matrix multiplication with bounds clipping. """

    def __init__(self, *args:Sequence[int], lower_bound:Sequence[int]=None, upper_bound:Sequence[int]=None) -> None:
        self._mat = args          # Tuple of integer sequences to form a matrix.
        self._low = lower_bound   # Lower bounds on each factor.
        self._high = upper_bound  # Upper bounds on each factor.

    def __matmul__(self, col:Sequence[int]) -> Sequence[int]:
        """ Multiply the vector <col> by this matrix and return the resulting column vector. """
        return [sum([a * b for a, b in zip(row, col)]) for row in self._mat]

    @lru_cache(maxsize=None)
    def __call__(self, *col:int) -> Sequence[int]:
        """ Combine all factors using matrix multiplication, clip at the optional bounds and cache the results. """
        val = self @ col
        if self._low is not None:
            val = map(max, val, self._low)
        if self._high is not None:
            val = map(min, val, self._high)
        return tuple(val)

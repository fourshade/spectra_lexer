""" Module for primitive operations consisting of drawing simple lines of text. """
from functools import partial

from spectra_lexer.graph.text.layout.canvas import Canvas
from spectra_lexer.graph.text.layout.pattern import Pattern


class Primitive:
    """ An abstract object whose job is to write text to a canvas. """

    height: int = 1  # Height in rows. Some subclasses may declare this as a property.
    width: int = 1   # Width in columns. Some subclasses may declare this as a property.

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the object on the text canvas. By default it does nothing. """


class PrimitiveString(Primitive):
    """ An abstract object whose job is to write a tagged text string to a canvas. """

    src: str = ""       # String to draw (may not be used).
    tag: object = None  # Identifier for the node.

    def __init__(self, s:str="", tag:object=None):
        """ By default, the rectangle starts at the origin and extends 1 unit down and to the right.
            Some subclasses may declare <size> to be a property. Do not attempt to set it. """
        self.src = s
        self.tag = tag


class PrimitiveRow(PrimitiveString):
    """ Writes tagged text to a row of a canvas. """

    def __init__(self, s:str, tag:object):
        """ By default, the rectangle starts at the origin and extends to the right. """
        super().__init__(s, tag)
        self.width = len(s)

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the string on the text canvas starting at the upper-left going right. """
        canvas.write_row(self.src, self.tag, row, col)


class PrimitiveColumn(PrimitiveString):
    """ Writes tagged text to a column of a canvas. """

    def __init__(self, s:str, tag:object):
        """ By default, the rectangle starts at the origin and extends down. """
        super().__init__(s, tag)
        self.height = len(s)

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the string on the text canvas starting at the upper-left going down. """
        canvas.write_column(self.src, self.tag, row, col)


class PrimitiveRowReplace(PrimitiveString):
    """ Replaces every space in the given row with its character. """

    width = 0  # Substitution operations should advance one row, but no columns.

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Replace every space in the row with unowned separators. """
        canvas.row_str_op(row, str.replace, " ", self.src)


# Primitive constructors for the main node text body.
PrimitiveBody = PrimitiveRow  # This one happens to be identical to a base primitive type.
PrimitiveSeparator = lambda *args: PrimitiveRowReplace(Pattern.SEPARATORS(1))  # This one ignores its arguments.


def PrimitiveSymbol(prim_cls:type, symbol_cls:type, length:int, tag:object) -> PrimitiveString:
    """ Partial setup function for creating primitives with many different symbol sets. """
    return prim_cls(symbol_cls(length), tag)


# Primitive constructors with specific symbols for node graphics.
# These can be safely used as class attributes; partial() functions are not bound as methods.
PrimitiveConnector = partial(PrimitiveSymbol, PrimitiveColumn, Pattern.CONNECTORS)
PrimitiveEndpiece = partial(PrimitiveSymbol, PrimitiveRow, Pattern.END)
PrimitiveContainerTop = partial(PrimitiveSymbol, PrimitiveRow, Pattern.TOP)
PrimitiveContainerBottom = partial(PrimitiveSymbol, PrimitiveRow, Pattern.BOTTOM)
PrimitiveContainerInversion = partial(PrimitiveSymbol, PrimitiveRow, Pattern.INV)
PrimitiveContainerUnmatchedMid = partial(PrimitiveSymbol, PrimitiveRow, Pattern.BAD_MIDDLE)
PrimitiveContainerUnmatchedEnd = partial(PrimitiveSymbol, PrimitiveRow, Pattern.BAD_END)

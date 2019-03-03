""" Module for primitive operations consisting of drawing simple lines of text. """

from spectra_lexer.interactive.graph.generator.canvas import Canvas


class _Primitive:
    """ Abstract object to write text to a canvas. Defines a rectangle size, a source string, and a node tag.
        No attribute is consistently used by every subclass, so __init__ is not defined here. """

    height: int = 1     # Height in rows. Some subclasses may declare this as a property.
    width: int = 1      # Width in columns. Some subclasses may declare this as a property.
    src: str = ""       # String to draw (may not be used).
    tag: object = None  # Identifier for the node (may not be used).

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the object on the text canvas. By default, nothing happens. """

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self.src!r}>"


class Primitive(_Primitive):
    """ A collection of simple classes for drawing lines and columns of text. """

    class Row(_Primitive):
        """ Writes tagged text to a row of a canvas. """

        def __init__(self, s:str, tag:object):
            """ The row starts at the origin and extends to the right. """
            self.src = s
            self.tag = tag
            self.width = len(s)

        def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
            """ Draw the string on the text canvas starting at the upper-left going right. """
            canvas.write_row(self.src, self.tag, row, col)

    class Column(_Primitive):
        """ Writes tagged text to a column of a canvas. """

        def __init__(self, s:str, tag:object):
            """ The column starts at the origin and extends down. """
            self.src = s
            self.tag = tag
            self.height = len(s)

        def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
            """ Draw the string on the text canvas starting at the upper-left going down. """
            canvas.write_column(self.src, self.tag, row, col)

    class RowReplace(_Primitive):
        """ Replaces every space in the given row with its character. """

        width = 0  # Row substitution operations should advance one row, but no columns.

        def __init__(self, s:str, *args):
            self.src = s

        def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
            """ Replace every space in the row with unowned separators. """
            canvas.row_str_op(row, str.replace, " ", self.src)

    class ColumnReplace(_Primitive):
        """ Replaces every space in the given column with its character. """

        height = 0  # Column substitution operations should advance one column, but no rows.

        def __init__(self, s:str, *args):
            self.src = s

        def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
            """ Replace every space in the column with unowned separators. """
            canvas.col_str_op(col, str.replace, " ", self.src)

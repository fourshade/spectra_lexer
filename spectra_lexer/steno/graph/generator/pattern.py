""" Module controlling the general appearance of text graph patterns and character sets. """

from .primitive import Primitive
from spectra_lexer.utils import memoize


class Pattern:
    """ A pattern consisting of a line of repeated characters with the first and last characters being unique. """

    def __new__(cls, primitive_cls:type, single:str, pattern:str=None):
        """ Return a memoized primitive generator for a variable-length pattern based on a specific character set.
            primitive_cls - Primitive class specifying how the characters are written to the canvas.
            single - A single character used when (and only when) the pattern is length 1.
            pattern - A sequence of 3 characters. If None, the single character fills in for all three:
                first - Starting character for all patterns with length > 1.
                middle - A character repeated to fill the rest of the space in all patterns with length > 2.
                last - Ending character for all patterns with length > 1. """
        first, middle, last = (pattern or single * 3)
        @memoize
        def constructor(length:int) -> str:
            """ Return a pattern string with unique ends based on a set of construction symbols and a length. """
            if length < 2:
                return single
            return first + middle * (length - 2) + last
        def make_primitive(length:int, tag:str):
            """ Create a primitive to write this pattern with the given length and tag to a canvas. """
            return primitive_cls(constructor(length), tag)
        return make_primitive

    @classmethod
    def Row(cls, *args):
        return cls(Primitive.Row, *args)

    @classmethod
    def Column(cls, *args):
        return cls(Primitive.Column, *args)


class PatternSpec:
    """ An empty pattern specification; no primitives are created at all. Useful as a base class. """
    TEXT = BOTTOM = TOP = CONNECTOR = ENDPIECE = CUSTOM = None


class PatternNode(PatternSpec):
    """ A default node. Uses text patterns consisting of a repeated character terminated by endpieces. """
    TEXT = Primitive.Row                # Primitive constructor for the text itself.
    BOTTOM = Pattern.Row("│", "├─┐")    # Primitive constructor for the section above the text.
    TOP = Pattern.Row("│", "├─┘")       # Primitive constructor for the section below the text.
    CONNECTOR = Pattern.Column("│")     # Primitive constructor for vertical connectors.
    ENDPIECE = Pattern.Row("┐", "┬┬┐")  # Primitive constructor for extension connectors.


class PatternThick(PatternNode):
    """ An important node with thicker connecting lines. """
    BOTTOM = Pattern.Row("║", "╠═╗")
    TOP = Pattern.Row("║", "╠═╝")
    CONNECTOR = Pattern.Column("║")
    ENDPIECE = Pattern.Row("╗", "╦╦╗")


class PatternThickVert(PatternNode):
    """ A node with thicker vertical connecting lines. """
    BOTTOM = Pattern.Row("║", "╟─╖")
    TOP = Pattern.Row("║", "╟─╜")
    CONNECTOR = Pattern.Column("║")
    ENDPIECE = Pattern.Row("╖", "╥╥╖")


class PatternThickHoriz(PatternNode):
    """ A node with thicker horizontal connecting lines. """
    BOTTOM = Pattern.Row("│", "╞═╕")
    TOP = Pattern.Row("│", "╞═╛")
    CONNECTOR = Pattern.Column("│")
    ENDPIECE = Pattern.Row("╕", "╤╤╕")


class PatternInversion(PatternThick):
    """ A node whose rule describes an inversion of steno order. These show arrows to indicate reversal. """
    BOTTOM = Pattern.Row("║", "◄═►")


class PatternUnmatched(PatternNode):
    """ A set of unmatched keys. These have broken connectors ending in question marks on both sides. """
    TOP = Pattern.Row("¦")
    CUSTOM = Pattern.Row("?")
    BOTTOM = CONNECTOR = None


class PatternSeparators(PatternSpec):
    """ A row of stroke separators. These are not connected to anything and have no owner. """
    TEXT = Primitive.RowReplace


class PatternSeparatorSingle(PatternSpec):
    """ A single stroke separator, not connected to anything. """
    TEXT = Primitive.Row

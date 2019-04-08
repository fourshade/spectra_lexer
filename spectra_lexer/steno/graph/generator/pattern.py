""" Module controlling the general appearance of text graph patterns and character sets. """

from .primitive import Primitive
from spectra_lexer.utils import memoize


class Symbols:
    """ Creates primitives to write symbol patterns with a given length to a canvas. """

    def __new__(cls, primitive:type, single:str, sides:str, middle:str):
        """ Return a memoized version of a symbol generator for a specific symbol set and primitive type.  """
        @memoize
        def constructor(length:int) -> str:
            """ Return a variable-length pattern string with unique ends based on a set of construction symbols.
                single - A single character used when (and only when) the pattern is length 1.
                sides -  A pair of characters used at either end of patterns longer than 1 character.
                middle - A character repeated to fill the rest of the space in patterns longer than 2 characters. """
            if length < 2:
                return single
            (left, right) = sides
            return left + middle * (length - 2) + right
        def make_primitive(length:int, tag:str):
            return primitive(constructor(length), tag)
        return make_primitive

    @classmethod
    def Row(cls, *args):
        return cls(Primitive.Row, *args)

    @classmethod
    def Column(cls, *args):
        return cls(Primitive.Column, *args)


class Pattern:
    """ An empty pattern; no primitives are created at all. Useful as a base class. """
    TEXT = BOTTOM = TOP = CONNECTOR = ENDPIECE = CUSTOM = None


class PatternNode(Pattern):
    """ A default node. Uses text patterns consisting of a repeated character terminated by endpieces. """
    TEXT = Primitive.Row                        # Primitive constructor for the text itself.
    BOTTOM = Symbols.Row("│", "├┐", "─")        # Primitive constructor for the section above the text.
    TOP = Symbols.Row("│", "├┘", "─")           # Primitive constructor for the section below the text.
    CONNECTOR = Symbols.Column("│", "││", "│")  # Primitive constructor for vertical connectors.
    ENDPIECE = Symbols.Row("┐", "┬┐", "┬")      # Primitive constructor for extension connectors.


class PatternThick(PatternNode):
    """ An important node with thicker connecting lines. """
    BOTTOM = Symbols.Row("║", "╠╗", "═")
    TOP = Symbols.Row("║", "╠╝", "═")
    CONNECTOR = Symbols.Column("║", "║║", "║")
    ENDPIECE = Symbols.Row("╗", "╦╗", "╦")


class PatternThickVert(PatternNode):
    """ A node with thicker vertical connecting lines. """
    BOTTOM = Symbols.Row("║", "╟╖", "─")
    TOP = Symbols.Row("║", "╟╜", "─")
    CONNECTOR = Symbols.Column("║", "║║", "║")
    ENDPIECE = Symbols.Row("╖", "╥╖", "╥")


class PatternThickHoriz(PatternNode):
    """ A node with thicker horizontal connecting lines. """
    BOTTOM = Symbols.Row("│", "╞╕", "═")
    TOP = Symbols.Row("│", "╞╛", "═")
    CONNECTOR = Symbols.Column("│", "││", "│")
    ENDPIECE = Symbols.Row("╕", "╤╕", "╤")


class PatternInversion(PatternThick):
    """ A node whose rule describes an inversion of steno order. These show arrows to indicate reversal. """
    BOTTOM = Symbols.Row("║", "◄►", "═")


class PatternUnmatched(PatternNode):
    """ A set of unmatched keys. These have broken connectors ending in question marks on both sides. """
    TOP = Symbols.Row("¦", "¦¦", "¦")
    CUSTOM = Symbols.Row("?", "??", "?")
    BOTTOM = CONNECTOR = None


class PatternSeparators(Pattern):
    """ A row of stroke separators. These are not connected to anything and have no owner. """
    TEXT = Primitive.RowReplace


class PatternSeparatorSingle(Pattern):
    """ A single stroke separator, not connected to anything. """
    TEXT = Primitive.Row

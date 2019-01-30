""" Module controlling the general appearance of text graph patterns and character sets. """

from typing import NamedTuple

from spectra_lexer.utils import memoize_one_arg


class _Symbols(NamedTuple):
    """ String constructor class for variable-length lines of standard text graph symbols. """

    single: str  # A single character used when (and only when) the pattern is length 1.
    sides: str   # A pair of characters used at either end of patterns longer than 1 character.
    middle: str  # A character repeated to fill the rest of the space in patterns longer than 2 characters.

    @classmethod
    def cached(cls, *symbols:str) -> callable:
        """ Return a memoized version of a symbol generator for a specific symbol set. """
        self = cls(*symbols)
        return memoize_one_arg(self.__call__)

    def __call__(self, length:int) -> str:
        """ Return a variable-length pattern string with unique ends based on a set of construction symbols. """
        # If the pattern is only a single character wide, use the unique "single" symbol.
        if length < 2:
            return self.single
        # If the pattern is two characters wide, use just the left and right symbols.
        sides = self.sides
        if length == 2:
            return sides
        # Otherwise put the left and right symbols at the ends and repeat the middle one inside to cover the rest.
        (left, right) = sides
        middle = self.middle * (length - 2)
        return left + middle + right


class Pattern:
    """ Symbols used to represent text patterns consisting of a repeated character terminated by endpieces. """
    TOP = _Symbols.cached("│", "├┘", "─")
    BOTTOM = _Symbols.cached("│", "├┐", "─")
    INV = _Symbols.cached("│", "◄►", "═")
    END = _Symbols.cached("┐", "┬┐", "┬")
    BAD_MIDDLE = _Symbols.cached("|", "||", "|")
    BAD_END = _Symbols.cached("?", "??", "?")
    CONNECTORS = _Symbols.cached("│", "││", "│")
    SEPARATORS = _Symbols.cached("/", "//", "/")
    # S_BEND = _Symbols.cached("│", "└┐", "─")
    # Z_BEND = _Symbols.cached("│", "┌┘", "─")

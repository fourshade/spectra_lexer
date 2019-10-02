""" Module for styling the appearance of text graphs. """

from typing import List


class IConnectors:
    """ Interface for a node connector character set. """

    __slots__ = ()

    def strlist(self, height:int) -> List[str]:
        """ Return a list of strings. The one at index 0 goes under the parent, then extends to <height>. """
        raise NotImplementedError


class CharPattern(dict):
    """ Memoized constructor for a variable-length pattern based on a specific character set.
        Each pattern consists of a line of repeated characters with the first and last characters being unique.
        single - A single character used when (and only when) the pattern is length 1.
        pattern - A sequence of 3 characters:
            first - Starting character for all patterns with length > 1.
            middle - A character repeated to fill the rest of the space in all patterns with length > 2.
            last - Ending character for all patterns with length > 1. """

    def __init__(self, single:str, pattern:str=None) -> None:
        super().__init__({0: "", 1: single})
        self._pattern = (pattern or single * 3)

    __call__ = dict.__getitem__

    def __missing__(self, length:int) -> str:
        """ Make a pattern string with unique ends based on the construction symbols and length. """
        first, middle, last = self._pattern
        s = self[length] = first + middle * (length - 2) + last
        return s


class SimpleConnectors(IConnectors):
    """ A standard set of connector characters joining a node to its parent. """

    __slots__ = ("_t_len", "_b_len")

    _endpiece = CharPattern("┐", "┬┬┐")  # Pattern constructor for extension connectors.
    _top = CharPattern("│", "├─┘")       # Pattern constructor for the section below the text.
    _connector = CharPattern("│")        # Pattern constructor for vertical connectors.
    _bottom = CharPattern("│", "├─┐")    # Pattern constructor for the section above the text.

    def __init__(self, t_len:int, b_len:int) -> None:
        self._t_len = t_len  # Length in columns of the attachment to the parent node.
        self._b_len = b_len  # Length in columns of the attachment to the child node.

    def strlist(self, height:int) -> List[str]:
        """ Add corner ┐ endpieces under the parent. These are only seen when connectors run off the right end.
            Add a top container ├--┘ directly below the parent. We always need these at minimum. """
        t_len = self._t_len
        items = [self._endpiece(t_len), self._top(t_len)]
        # If there's a wide gap, add a connector between the containers.
        gap_height = height - 3
        if gap_height > 0:
            items += self._connector(gap_height)
        # If there's a space available, add a bottom container ├--┐ at the end.
        if height > 2:
            items.append(self._bottom(self._b_len))
        return items


class UnmatchedConnectors(SimpleConnectors):
    """ A set of broken connectors with a single-row gap. Used for unmatched keys. """

    __slots__ = ()

    def strlist(self, height:int) -> List[str]:
        """ Unmatched key sets only occur at the end of rules. Use only the bottom length. """
        b_len = self._b_len
        connector_row = "¦" * b_len
        upper_connectors = [connector_row] * (height - 5)
        ending_row = "?" * b_len
        return [self._endpiece(b_len),
                *upper_connectors,
                ending_row,
                "",
                ending_row,
                connector_row]


class ThickConnectors(SimpleConnectors):
    """ A set of connectors with thicker lines for important nodes. """

    __slots__ = ()

    _endpiece = CharPattern("╖", "╥╥╖")
    _top = CharPattern("║", "╠═╝")
    _connector = CharPattern("║")
    _bottom = CharPattern("║", "╠═╗")


class InversionConnectors(ThickConnectors):
    """ A set of thick connectors showing arrows to indicate an inversion of steno order. """

    __slots__ = ()

    _bottom = CharPattern("║", "◄═►")


class LinkedConnectors(ThickConnectors):
    """ A set of thick connectors marking two strokes linked together. """

    __slots__ = ()

    _top = CharPattern("♦", "♦═╝")
    _connector = CharPattern("♦")
    _bottom = CharPattern("♦", "♦═╗")

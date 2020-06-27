""" Styles for the appearance of line connectors in text graphs. """

from . import ConnectorRows, IConnectors


class NullConnectors(IConnectors):
    """ An empty set of connectors. """

    __slots__ = ()

    def rows(self, height:int) -> ConnectorRows:
        return iter(())

    def min_height(self) -> int:
        return 0


class _CharPattern(dict):
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

    _endpieces = _CharPattern("┐", "┬┬┐")  # Pattern constructor for extension connectors.
    _top = _CharPattern("│", "├─┘")        # Pattern constructor for the section below the text.
    _connectors = _CharPattern("│")        # Pattern constructor for vertical connectors.
    _bottom = _CharPattern("│", "├─┐")     # Pattern constructor for the section above the text.

    def __init__(self, t_len:int, b_len:int) -> None:
        self._t_len = t_len or 1  # Length in columns of the attachment to the parent node.
        self._b_len = b_len or 1  # Length in columns of the attachment to the child node.

    def rows(self, height:int) -> ConnectorRows:
        """ Yield a row of endpieces ┬┬┐ under the parent. These are only seen when connectors run off the right end.
            Then yield a top container ├--┘ directly below the parent. We always need these at minimum. """
        t_len = self._t_len
        yield self._endpieces(t_len)
        yield self._top(t_len)
        # If there's a wide gap, yield connectors to go between the containers.
        gap_height = height - 3
        if gap_height > 0:
            yield from self._connectors(gap_height)
        # If there's a space available, yield a bottom container ├--┐ at the end.
        if height > 2:
            yield self._bottom(self._b_len)

    def min_height(self) -> int:
        """ Minimum height is 3 characters, or 2 if the bottom attachment is one character wide. """
        if self._b_len == 1:
            return 2
        else:
            return 3


class UnmatchedConnectors(IConnectors):
    """ A set of broken connectors with a single-row gap. Used for unmatched keys. """

    __slots__ = ("_b_len",)

    _endpieces = _CharPattern("┐", "┬┬┐")
    _connectors = _CharPattern("¦")
    _terminators = _CharPattern("?")

    def __init__(self, b_len:int) -> None:
        self._b_len = b_len or 1  # Length in columns of the attachment to the child node.

    def rows(self, height:int) -> ConnectorRows:
        """ Unmatched key sets only occur at the end of rules. We only need the bottom length. """
        b_len = self._b_len
        connector_row = self._connectors(b_len)
        ending_row = self._terminators(b_len)
        yield self._endpieces(b_len)
        for _ in range(height - 5):
            yield connector_row
        yield ending_row
        yield ""
        yield ending_row
        yield connector_row

    def min_height(self) -> int:
        """ These connectors require at least 6 characters to show the full gap. """
        return 6


class ThickConnectors(SimpleConnectors):
    """ A set of connectors with thicker lines for important nodes. """

    __slots__ = ()

    _endpieces = _CharPattern("╖", "╥╥╖")
    _top = _CharPattern("║", "╠═╝")
    _connectors = _CharPattern("║")
    _bottom = _CharPattern("║", "╠═╗")


class InversionConnectors(ThickConnectors):
    """ A set of thick connectors showing arrows to indicate an inversion of steno order. """

    __slots__ = ()

    _bottom = _CharPattern("║", "◄═►")


class LinkedConnectors(ThickConnectors):
    """ A set of thick connectors marking two strokes linked together. """

    __slots__ = ()

    _top = _CharPattern("♦", "♦═╝")
    _connectors = _CharPattern("♦")
    _bottom = _CharPattern("♦", "♦═╗")

""" Module for the lowest-level text rendering operations. Performance is more critical than readability here. """

from collections import namedtuple
from typing import Iterable, List, Sequence, Tuple

from ..rules import StenoRule


class BaseConnectors:
    """ Base class for a node connector character set. """

    bold = False  # If True, this node's text (but not connectors) will be bold in markup.

    def min_height(self) -> int:
        """ Return the minimum connector height, including the parent row but excluding the child row. """
        return 0

    def strlist(self, height:int) -> List[str]:
        """ Return a list of strings. The one at index 0 goes under the parent, then extends to <height>. """
        return [""] * height


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

    def __missing__(self, length:int) -> str:
        """ Make a pattern string with unique ends based on the construction symbols and length. """
        first, middle, last = self._pattern
        s = self[length] = first + middle * (length - 2) + last
        return s


class SimpleConnectors(namedtuple("SimpleConnectors", "t_len b_len"), BaseConnectors):
    """ A standard set of connector characters joining a node to its parent. """
    _endpiece =  CharPattern("┐", "┬─┐")  # Pattern constructor for extension connectors.
    _top =       CharPattern("│", "├─┘")  # Pattern constructor for the section below the text.
    _connector = CharPattern("│")         # Pattern constructor for vertical connectors.
    _bottom =    CharPattern("│", "├─┐")  # Pattern constructor for the section above the text.

    def min_height(self) -> int:
        """ Minimum height is 3 characters, or 2 if the bottom is one unit wide. """
        return 3 - (self.b_len == 1)

    def strlist(self, height:int) -> List[str]:
        """ Add corner ┐ endpieces under the parent for when connectors run off the end.
            Add a top container ├--┘ below the parent. We always need these at minimum. """
        t_len, b_len = self
        items = [self._endpiece[t_len], self._top[t_len]]
        # If there's a wide gap, add a connector between the containers.
        gap_height = height - 3
        if gap_height > 0:
            items += self._connector[gap_height]
        # If there's a space available, add a bottom container ├--┐ at the end.
        if height > 2:
            items.append(self._bottom[b_len])
        return items


class UnmatchedConnectors(SimpleConnectors):
    """ A set of unmatched keys with broken connectors ending in question marks on both sides. """

    _endpiece = CharPattern("┐", "┬┬┐")

    def min_height(self) -> int:
        """ This connector requires at least 6 characters to show the full gap. """
        return 6

    def strlist(self, height:int) -> List[str]:
        """ Unmatched key sets only occur at the end of rules. Use only the bottom length. """
        t_len, b_len = self
        top = ["¦" * b_len] * (height - 5)
        return [self._endpiece[b_len], *top, "?" * b_len, "", "?" * b_len, "¦" * b_len]


class ThickConnectors(SimpleConnectors):
    """ A pattern for important nodes with thicker connecting lines and boldface. """
    bold = True
    _endpiece =  CharPattern("╗", "╦═╗")
    _top =       CharPattern("║", "╠═╝")
    _connector = CharPattern("║")
    _bottom =    CharPattern("║", "╠═╗")


class InversionConnectors(ThickConnectors):
    """ Pattern for nodes describing an inversion of steno order. These show arrows to indicate reversal. """
    _bottom =    CharPattern("║", "◄═►")


class LinkedConnectors(ThickConnectors):
    """ Pattern for nodes describing two strokes linked together. """
    _top =       CharPattern("♦", "♦═╝")
    _connector = CharPattern("♦")
    _bottom =    CharPattern("♦", "♦═╗")


class Canvas(List[list]):
    """ A mutable 2D grid-like document structure that has metadata reference objects associated with strings.
        Each string should contain exactly one printable character, with additional optional markup.
        For performance, the implementation is low-level: each row is a list with alternating strings and refs.
        No bounds checking is done. Operations may span multiple rows, and should be optimized for map(). """

    def __init__(self, rows:int, cols:int) -> None:
        """ Make a new, blank grid of spaces and None references by copying a single line repeatedly. """
        super().__init__(map(list.copy, [[" "] * cols] * rows))
        self.refs = [*map(list.copy, [[None] * cols] * rows)]

    def write_row(self, seq:Sequence[str], ref:object=None, row:int=0, col:int=0, _len=len) -> None:
        """ Writes a string <seq>uence with a single <ref> across a row with the top-left starting at <row, col>.
            This is the most performance-critical method in graphing, called hundreds of times per frame.
            Avoid method call overhead by inlining everything and using slice assignment over list methods. """
        r = self[row]
        t = self.refs[row]
        length = _len(seq)
        if length == 1:  # fast path: <seq> contains one string.
            r[col] = seq[0]
            t[col] = ref
            return
        if col < 0:  # slow path: <seq> is arbitrarily long.
            raise IndexError(col)
        end = col + length
        r[col:end] = seq
        t[col:end] = [ref] * length

    def write_column(self, seq:Sequence[str], ref:object=None, row:int=0, col:int=0) -> None:
        """ Like write_row(), but writes the strings down a column instead of across a row.
            This is much slower because a different list must be accessed and written for every item. """
        refs = self.refs
        for c in seq:
            self[row][col] = c
            refs[row][col] = ref
            row += 1

    def row_replace(self, row:int, *args) -> None:
        """ Simulate a string replace operation on an entire row without altering any refs. """
        r = self[row]
        r[:] = "".join(r).replace(*args)

    def __str__(self) -> str:
        """ Return the rendered text grid followed by a grid of numbers representing each distinct ref. """
        refs = self.refs
        unique_refs = set().union(*refs) - {None}
        ref_chars = {r: chr(i) for i, r in enumerate(unique_refs, ord('0'))}
        ref_chars[None] = ' '
        sects = []
        for line, rline in zip(self, refs):
            sects += [*line, *map(ref_chars.get, rline), "\n"]
        return "".join(sects)


class IPrimitive:
    """ Abstract primitive for operations consisting of drawing lines and columns of text to a canvas. """

    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        """ Draw the object on <canvas> with an offset of <row, col>. """
        raise NotImplementedError


class RowPrimitive(namedtuple("PRow", "text ref"), IPrimitive):
    """ Writes a text string to a row of a canvas starting at the upper-left going right. """
    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        canvas.write_row(self.text, self.ref, row, col)


class StrListPrimitive(namedtuple("PConn", "strlist ref"), IPrimitive):
    """ Writes a left-aligned string list to a canvas. """
    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        for s in self.strlist:
            canvas.write_row(s, self.ref, row, col)
            row += 1


class ReplacePrimitive(namedtuple("PReplace", "orig repl"), IPrimitive):
    """ Replace every occurence of <orig> in a row with unowned copies of <repl>. """
    def write(self, canvas:Canvas, row:int=0, col:int=0) -> None:
        canvas.row_replace(row, self.orig, self.repl)


class GraphNode:
    """ Abstract class representing a visible node in a tree structure of steno rules.
        Each node may have zero or more children and zero or one parent of the same type. """

    def __init__(self, text:str, bstart:int, blen:int, tstart:int, tlen:int, connector:BaseConnectors) -> None:
        self._text = text            # Text characters drawn on the last row as the node's "body".
        self._bottom_start = bstart  # Index of the starting character of the attachment to this node's body.
        self._bottom_length = blen   # Length in characters of the attachment to this node's body.
        self._attach_start = tstart  # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen   # Length in characters of the attachment to the parent node.
        self._height = 1             # Total height in rows.
        self._width = blen           # Total width in columns.
        self._connector = connector  # Pattern constructor for connectors.

    def attach_range(self) -> range:
        start = self._attach_start
        return range(start, start + self._attach_length)

    def layout_params(self) -> Tuple[int, int, int, int]:
        return self._attach_start, self._height, self._width, self._connector.min_height()

    def resize(self, heights, widths) -> None:
        """ Recalculate total width and height from the max child dimensions and self. """
        widths.append(self._width)
        heights.append(self._height)
        self._height = max(widths)
        self._width = max(heights)

    def shift(self, items, row:int) -> List[Tuple[IPrimitive, int, int]]:
        return [(item, r + row, c + self._attach_start) for (item, r, c) in items]

    def body(self) -> Tuple[IPrimitive, int, int]:
        """ The main primitive is a text row starting at the origin (optionally shifted to account for hyphens). """
        return RowPrimitive(self._text, self), 0, -self._bottom_start

    def connect(self, row:int) -> List[Tuple[IPrimitive, int, int]]:
        """ Yield primitives representing this node relative to its parent.
            The origin is the top-left corner of the parent, and the child should be <row> below it. """
        return [(StrListPrimitive(self._connector.strlist(row), self), 0, self._attach_start)]

    def bold(self) -> bool:
        return self._connector.bold


class SeparatorNode(GraphNode):
    """ The singular stroke separator is not connected to anything. It may be removed by the layout. """

    def body(self) -> Tuple[IPrimitive, int, int]:
        """ Replace every space in a row with the separator. """
        return ReplacePrimitive(" ", self._text), 0, 0


class NodeFactory:

    def __init__(self, sep:str, ignored:Iterable[str]='-') -> None:
        self._key_sep = sep           # Steno key used as stroke separator.
        self._ignored = set(ignored)  # Tokens to ignore at the beginning of key strings (usually the hyphen '-')

    def make_root(self, rule:StenoRule) -> GraphNode:
        """ The root node's attach points are arbitrary, so tstart=0 and tlen=blen. """
        return self.make_node(rule, 0, len(rule.letters))

    def make_node(self, rule:StenoRule, tstart:int, tlen:int) -> GraphNode:
        """ Derived rules (i.e. branch nodes) show their letters. Base rules (i.e. leaf nodes) show their keys. """
        node_cls = GraphNode
        flags = rule.flags
        bstart = 0
        if not tlen:
            tlen = 1
        if rule.rulemap:
            text = letters = rule.letters
            blen = len(letters)
            if flags.inversion:
                connector = InversionConnectors(tlen, blen)
            elif flags.linked:
                connector = LinkedConnectors(tlen, blen)
            else:
                connector = ThickConnectors(tlen, blen)
        else:
            text = keys = rule.keys
            blen = len(keys)
            # The text is shifted left if the keys start with an ignored token.
            if blen > 1 and keys[0] in self._ignored:
                bstart += 1
                blen -= 1
            if keys == self._key_sep:
                node_cls = SeparatorNode
                connector = BaseConnectors()
            elif flags.unmatched:
                connector = UnmatchedConnectors(tlen, blen)
            else:
                connector = SimpleConnectors(tlen, blen)
        return node_cls(text, bstart, blen, tstart, tlen, connector)

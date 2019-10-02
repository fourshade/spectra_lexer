""" Module for the lowest-level text graphing operations. """

from functools import lru_cache
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from .layout import BaseGraphLayout
from .render import Canvas
from ..rules import StenoRule


class IConnectors:
    """ Interface for a node connector character set. """

    __slots__ = ()

    def min_height(self) -> int:
        """ Return the minimum connector height, including the parent row but excluding the child row. """
        raise NotImplementedError

    def strlist(self, height:int) -> List[str]:
        """ Return a list of strings. The one at index 0 goes under the parent, then extends to <height>. """
        raise NotImplementedError


class NullConnectors(IConnectors):
    """ A blank connector set. Used for nodes such as separators that connect to nothing. """

    __slots__ = ()

    def min_height(self) -> int:
        return 0

    def strlist(self, height:int) -> List[str]:
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

    def min_height(self) -> int:
        """ Minimum height is 3 characters, or 2 if the bottom is one unit wide. """
        return 3 - (self._b_len == 1)

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

    def min_height(self) -> int:
        """ This connector requires at least 6 characters to show the full gap. """
        return 6

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


class IBody:
    """ Interface for a drawable node body. """

    __slots__ = ()

    def write(self, canvas:Canvas, row:int, col:int, **markup) -> None:
        raise NotImplementedError

    def write_partial(self, canvas:Canvas, row:int, col:int, start:int, stop:int, **markup) -> None:
        raise NotImplementedError


class StandardBody(IBody):
    """ This node text may have an additional shift offset. """

    __slots__ = ("_text", "_shift")

    def __init__(self, text:str, shift:int) -> None:
        self._text = text    # Text characters drawn on the last row as the node's "body".
        self._shift = shift  # Columns to shift this node's body relative to its attachment.

    def write(self, canvas:Canvas, row:int, col:int, **markup) -> None:
        """ Draw the text in a row after shifting to account for hyphens. """
        canvas.write_row(self._text, row, col + self._shift, **markup)

    def write_partial(self, canvas:Canvas, row:int, col:int, start:int, stop:int, **markup) -> None:
        """ Draw only a part of the text, in boldface. """
        canvas.write_row(self._text[start:stop], row, col + self._shift + start, bold=True, **markup)


class BoldBody(StandardBody):
    """ This node text is always bold in markup. """

    __slots__ = ()

    def write(self, *args, bold=..., **markup) -> None:
        """ Draw the text in boldface. """
        super().write(*args, bold=True, **markup)


class SeparatorBody(IBody):
    """ The singular stroke separator is not connected to anything. It may be removed by the layout. """

    __slots__ = ("_sep",)

    def __init__(self, sep:str) -> None:
        assert len(sep) == 1
        self._sep = sep  # Separator text, limited to one character.

    def write(self, canvas:Canvas, row:int, *args, **markup) -> None:
        """ Replace every space in <row> with the separator key using no markup. """
        canvas.replace_empty(self._sep, row)

    write_partial = write


class GraphNode:
    """ A visible node in a tree structure of steno rules. Each node may have zero or more children. """

    def __init__(self, tstart:int, tlen:int, blen:int, body:IBody, connector:IConnectors, depth:int, children:Sequence) -> None:
        self._attach_start = tstart  # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen   # Length in characters of the attachment to the parent node.
        self._bwidth = blen          # Body width in columns.
        self._body = body            # Renderer for the node text body.
        self._connector = connector  # Pattern constructor for connectors.
        self._depth = depth          # Nesting depth of this node.
        self._children = children    # Direct children of this node.

    def __iter__(self) -> Iterator:
        """ Yield all descendants of this node recursively depth-first. """
        yield self
        for child in self._children:
            yield from child

    def lineage(self, node) -> Sequence:
        """ Return <node>'s ancestors in order, starting with self at index 0 and ending with <node>. """
        if node is self:
            return [self]
        for child in self._children:
            lineage = child.lineage(node)
            if lineage:
                return [self, *lineage]
        return ()

    def layout(self, layout:BaseGraphLayout) -> Sequence[tuple]:
        """ Arrange each child node in rows and return a nested sequence containing the nodes and their positions. """
        min_row = self._connector.min_height()
        min_col = self._attach_start
        height = 1
        width = self._bwidth
        items = []
        children = self._children
        if children:
            child_params = []
            for child in children:
                # Children are recursively laid out first to determine their height and width.
                mrow, mcol, h, w, c_items = child.layout(layout)
                child_params.append([mrow, mcol, h, w, child, c_items])
            layout.arrange_rows(child_params)
            all_heights = [height]
            all_widths = [width]
            # Reverse the composition order to ensure that the leftmost objects get drawn last.
            for row, col, h, w, child, c_items in filter(None, reversed(child_params)):
                items.append((child, row, col, c_items))
                all_heights.append(row + h)
                all_widths.append(col + w)
            # Calculate total width and height from the maximum child dimensions.
            height = max(all_heights)
            width = max(all_widths)
        return min_row, min_col, height, width, items

    def write(self, canvas:Canvas, top_row:int, bottom_row:int, col:int,
              ref:str, intense:bool, target:Optional) -> None:
        # Write the non-formatted body first, then color only those columns shared with the terminal node.
        self._body.write(canvas, bottom_row, col, ref=ref)
        lineage = self.lineage(target) if target is not None else ()
        if lineage:
            color = self._color(bottom_row, self._depth, intense)
            color_col_range = (0, 10000)
            for node in lineage[1:]:
                color_col_range = node.column_intersection(*color_col_range)
            self._body.write_partial(canvas, bottom_row, col, *color_col_range, ref=ref, color=color)
        height = bottom_row - top_row
        if height:
            for s in self._connector.strlist(height):
                if lineage:
                    color = self._color(top_row, self._depth, intense)
                    canvas.write_row(s, top_row, col, ref=ref, color=color)
                else:
                    canvas.write_row(s, top_row, col, ref=ref)
                top_row += 1

    def column_intersection(self, parent_start:int, parent_end:int):
        """ (parent_start, parent_end) is the index range for columns spanned by this node's parent.
            Return a new (equal or smaller) range columns this child shares with it. """
        start = parent_start + self._attach_start
        end = min(parent_end, start + self._attach_length)
        return start, end

    @staticmethod
    @lru_cache(maxsize=None)
    def _color(row:int, depth:int, intense:bool) -> Tuple[int, int, int]:
        """ Return an RGB 0-255 color tuple based on a node's location and intensity. """
        if not depth:
            # The root node has a bright red color, or orange if selected.
            return 255, 120 * intense, 0
        # Start from pure blue. Add red with nesting depth, green with row index, and both with the intense flag.
        r = min(64 * depth - 64 * intense, 192)
        g = min(8 * row + 100 * intense, 192)
        b = 255
        return r, g, b


class NodeFactory:
    """ Creates text graph nodes from steno rules and map positions. """

    def __init__(self, *, ignored:Iterable[str]='-') -> None:
        self._ignored = set(ignored)  # Tokens to ignore at the beginning of key strings (usually the hyphen '-')

    def make_node(self, rule:StenoRule, tstart:int, tlen:int, depth:int, children:Sequence[GraphNode]) -> GraphNode:
        """ Make a new graph node based on a rule's properties and/or child count. """
        if not tlen:
            tlen = 1
        if children:
            # Derived rules (i.e. branch nodes) show their letters in boldface.
            text = rule.letters
            blen = len(text)
            body = BoldBody(text, 0)
            if rule.is_inversion:
                connector = InversionConnectors(tlen, blen)
            elif rule.is_linked:
                connector = LinkedConnectors(tlen, blen)
            else:
                connector = ThickConnectors(tlen, blen)
        else:
            # Base rules (i.e. leaf nodes) show their keys.
            text = rule.keys
            blen = len(text)
            if rule.is_separator:
                body = SeparatorBody(text)
                connector = NullConnectors()
            else:
                # The text is shifted left if it starts with (and does not consist solely of) an ignored token.
                bshift = 0
                if blen > 1 and text[0] in self._ignored:
                    bshift -= 1
                    blen -= 1
                body = StandardBody(text, bshift)
                if rule.is_unmatched:
                    connector = UnmatchedConnectors(tlen, blen)
                else:
                    connector = SimpleConnectors(tlen, blen)
        return GraphNode(tstart, tlen, blen, body, connector, depth, children)

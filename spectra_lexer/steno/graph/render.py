""" Module for the lowest-level text graphing operations. """

from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from ..rules import RuleMapItem, StenoRule


class BaseConnectors:
    """ Base class for a node connector character set. """

    __slots__ = ()

    def min_height(self) -> int:
        """ Return the minimum connector height, including the parent row but excluding the child row. """
        raise NotImplementedError

    def strlist(self, height:int) -> List[str]:
        """ Return a list of strings. The one at index 0 goes under the parent, then extends to <height>. """
        raise NotImplementedError


class NullConnectors(BaseConnectors):
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

    def __missing__(self, length:int) -> str:
        """ Make a pattern string with unique ends based on the construction symbols and length. """
        first, middle, last = self._pattern
        s = self[length] = first + middle * (length - 2) + last
        return s


class SimpleConnectors(BaseConnectors):
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
        items = [self._endpiece[t_len], self._top[t_len]]
        # If there's a wide gap, add a connector between the containers.
        gap_height = height - 3
        if gap_height > 0:
            items += self._connector[gap_height]
        # If there's a space available, add a bottom container ├--┐ at the end.
        if height > 2:
            items.append(self._bottom[self._b_len])
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
        return [self._endpiece[b_len],
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


class Canvas:
    """ A mutable 2D grid-like document structure that has metadata reference objects associated with strings.
        Each string should contain exactly one printable character, with additional optional markup. """

    _row_offset = 0  # Offset in rows to draw characters using special write methods.
    _col_offset = 0  # Offset in columns to draw characters using special write methods.

    def __init__(self, rows:int, cols:int) -> None:
        """ Make a new, blank grid of spaces and None references by copying a single line repeatedly. """
        self._chars = [*map(list.copy, [[" "] * cols] * rows)]
        self._refs = [*map(list.copy, [[None] * cols] * rows)]

    def write_row(self, seq:Sequence[str], ref:object, row:int, col:int) -> None:
        """ Write a string <seq>uence with a single <ref> across a row with the top-left starting at <row, col>.
            This is a serious hotspot during graphing; avoid method call overhead by inlining everything. """
        if col < 0:
            self._shift_cols(-col)
            col = 0
        char_row = self._chars[row]
        ref_row = self._refs[row]
        for s in seq:
            char_row[col] = s
            ref_row[col] = ref
            col += 1

    def _shift_cols(self, ncols:int) -> None:
        """ Pad the grid with columns to the left to compensate for an object attempting to draw at a negative index.
            Redirect drawing instance methods to draw relative to the the new zero point. """
        self._col_offset += ncols
        for c in self._chars:
            c[:0] = " " * ncols
        for r in self._refs:
            r[:0] = [None] * ncols
        self.write_row = self._write_row_offset

    def _write_row_offset(self, seq:Sequence[str], ref:object, row:int, col:int) -> None:
        """ If the origin has been shifted by padding, draw new rows with an offset. """
        self.__class__.write_row(self, seq, ref, row + self._row_offset, col + self._col_offset)

    def get_offset(self) -> Tuple[int, int]:
        """ Return the current origin offset. """
        return self._row_offset, self._col_offset

    def row_replace(self, row:int, *args) -> None:
        """ Simulate a string replace operation on an entire row without altering any refs. """
        r = self._chars[row + self._row_offset]
        r[:] = "".join(r).replace(*args)

    def chars(self) -> List[List[str]]:
        """ Return the raw text grid. """
        return self._chars

    def refs(self) -> List[list]:
        """ Return the raw reference grid. """
        return self._refs

    def __str__(self) -> str:
        """ Return the current text grid followed by a grid of numbers representing each distinct ref. """
        chars = self.chars()
        refs = self.refs()
        unique_refs = set().union(*refs) - {None}
        ref_chars = {r: chr(i) for i, r in enumerate(unique_refs, ord('0'))}
        ref_chars[None] = ' '
        sects = []
        for line, rline in zip(chars, refs):
            sects += [*line, *map(ref_chars.get, rline), "\n"]
        return "".join(sects)


class GraphNode:
    """ A visible node in a tree structure of steno rules. Each node may have zero or more children. """

    def __init__(self, text:str, bshift:int, blen:int, tstart:int, tlen:int,
                 bold:bool, connector:BaseConnectors, children=()) -> None:
        self._text = text            # Text characters drawn on the last row as the node's "body".
        self._body_shift = bshift    # Columns to shift this node's body relative to its attachment.
        self._attach_start = tstart  # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen   # Length in characters of the attachment to the parent node.
        self._height = 1             # Total height in rows.
        self._width = blen           # Total width in columns.
        self._bold = bold            # If True, this node's text (but not connectors) is always bold in markup.
        self._connector = connector  # Pattern constructor for connectors.
        self._children = children    # Direct children of this node.

    def __iter__(self) -> Iterator:
        return iter(self._children)

    def attach_range(self) -> range:
        start = self._attach_start
        return range(start, start + self._attach_length)

    def layout_params(self) -> Tuple[int, int, int, int]:
        """ Return all parameters needed for node layout. """
        return self._attach_start, self._height, self._width, self._connector.min_height()

    def resize(self, widths:List[int], heights:List[int]) -> None:
        """ Recalculate total width and height from the max child dimensions and self. """
        widths.append(self._width)
        heights.append(self._height)
        self._width = max(widths)
        self._height = max(heights)

    def write(self, canvas:Canvas, parent_row:int, this_row:int, this_col:int) -> None:
        """ Draw the text in this row starting at the relative origin (optionally shifted to account for hyphens).
            Then write the connector string list between this row and the parent if there is space. """
        canvas.write_row(self._text, self, this_row, this_col + self._body_shift)
        height = this_row - parent_row
        if height:
            for s in self._connector.strlist(height):
                canvas.write_row(s, self, parent_row, this_col)
                parent_row += 1

    def bold(self) -> bool:
        return self._bold


class SeparatorNode(GraphNode):
    """ The singular stroke separator is not connected to anything. It may be removed by the layout. """

    def write(self, canvas:Canvas, parent_row:int, this_row:int, this_col:int) -> None:
        """ Replace every space in this row with the separator key. """
        canvas.row_replace(this_row, " " * len(self._text), self._text)


class NodeFactory:
    """ Creates text graph nodes from steno rules and keeps indices matching these rules to their nodes. """

    def __init__(self, *, ignored:Iterable[str]='-', recursive=True) -> None:
        self._ignored = set(ignored)  # Tokens to ignore at the beginning of key strings (usually the hyphen '-')
        self._recursive = recursive   # If True, also create children of children and so on.
        self._nodes_by_name = {}      # Mapping of each rule's name to the node that used it last.
        self._rules_by_node = {}      # Mapping of each generated node to its rule.

    def lookup_node(self, rule_name:str) -> Optional[GraphNode]:
        """ Return the last recorded node that matches <rule_name>, if any. """
        return self._nodes_by_name.get(rule_name)

    def lookup_rule(self, node:GraphNode) -> Optional[StenoRule]:
        """ Return the rule from which <node> was built. """
        return self._rules_by_node.get(node)

    def make_root(self, rule:StenoRule) -> GraphNode:
        """ The root node's attach points are arbitrary, so tstart=0 and tlen=blen. """
        children = self._make_children(rule.rulemap)
        return self._make_node(rule, 0, len(rule.letters), children)

    def _make_children(self, rulemap:Sequence[RuleMapItem]) -> List[GraphNode]:
        """ Make child nodes from a rulemap. Only create grandchildren if recursion is allowed. """
        nodes = []
        for item in rulemap:
            rule = item.rule
            child_map = rule.rulemap
            if child_map and self._recursive:
                children = self._make_children(child_map)
            else:
                children = []
            nodes.append(self._make_node(rule, item.start, item.length, children))
        return nodes

    def _make_node(self, rule:StenoRule, tstart:int, tlen:int, children) -> GraphNode:
        """ Make a new graph node based on a rule's properties and/or child count. """
        node_cls = GraphNode
        bshift = 0
        if not tlen:
            tlen = 1
        if children:
            # Derived rules (i.e. branch nodes) show their letters in boldface.
            bold = True
            text = rule.letters
            blen = len(text)
            if rule.is_inversion:
                connector = InversionConnectors(tlen, blen)
            elif rule.is_linked:
                connector = LinkedConnectors(tlen, blen)
            else:
                connector = ThickConnectors(tlen, blen)
        else:
            # Base rules (i.e. leaf nodes) show their keys.
            bold = False
            text = keys = rule.keys
            blen = len(keys)
            # The text is shifted left if it starts with (and does not consist solely of) an ignored token.
            if blen > 1 and keys[0] in self._ignored:
                bshift -= 1
                blen -= 1
            if rule.is_separator:
                connector = NullConnectors()
                node_cls = SeparatorNode
            elif rule.is_unmatched:
                connector = UnmatchedConnectors(tlen, blen)
            else:
                connector = SimpleConnectors(tlen, blen)
        node = node_cls(text, bshift, blen, tstart, tlen, bold, connector, children)
        self._nodes_by_name[rule.name] = node
        self._rules_by_node[node] = rule
        return node

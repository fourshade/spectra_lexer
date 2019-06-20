""" Module for higher-level text objects such as graph nodes for text operations. """

from typing import Callable, Dict, Optional, Sequence

from .primitive import ClipMatrix, PatternColumn, PatternRow, PrimitiveRow, PrimitiveRowReplace
from spectra_lexer.resource import RuleFlags, StenoRule


class GraphNode:
    """ Abstract class representing a node in a tree structure of steno rules.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child sequence may be mutable, hashing is by identity only. """

    COLOR = ClipMatrix([0,   64,  0,   64],  # Vary red with nesting depth and selection (for purple),
                       [0,   0,   8,   0],   # vary green with the row index,
                       [255, 0,   0,   0],   # starting from pure blue,
                       upper_bound=(192, 192, 255))  # and stopping short of invisible white.

    BOTTOM = PatternRow("│", "├─┐")    # Primitive constructor for the section above the text.
    TOP = PatternRow("│", "├─┘")       # Primitive constructor for the section below the text.
    CONNECTOR = PatternColumn("│")     # Primitive constructor for vertical connectors.
    ENDPIECE = PatternRow("┐", "┬┬┐")  # Primitive constructor for extension connectors.

    parent = None            # Direct parent of the node. If None, it is the root node (or unconnected).
    children: Sequence = ()  # Direct children of the node.
    text: str                # Text characters drawn on the last row.
    attach_start: int        # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int       # Length of the attachment (may be different than its letters due to substitutions).
    depth: int               # Nesting depth of the node. It is 0 for the root, 1 for direct children, and so on.
    bottom_length: int       # Length of the bottom attach point. Is the length of the text unless start is !=0.

    def __init__(self, text:str, start:int, length:int, depth:int):
        self.text = text
        self.attach_start = start
        self.attach_length = length or 1
        self.depth = depth
        self.bottom_length = len(text)

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        raise NotImplementedError

    def connectors(self, write:Callable, row:int, col:int, p_width:int) -> None:
        """ Write connectors of a child at index <row, col>. The parent is by definition at row index 0.
            <p_width> is the total width of the parent, past which endpieces must be added. """
        # If there's a space available, add a bottom container ├--┐ next.
        if row > 2:
            write(self.BOTTOM(self.bottom_length), row - 1, col)
        # If the top container runs off the end, we need a corner ┐ endpiece.
        overhang = col - p_width + 1
        if overhang > 0:
            write(self.ENDPIECE(overhang), 0, col)
        # Add a top container ├--┘ near the parent. We always need this at minimum even with zero attach length.
        write(self.TOP(self.attach_length), 1, col)
        # If there's a gap, add a connector between the containers.
        gap_height = row - 3
        if gap_height > 0:
            write(self.CONNECTOR(gap_height), 2, col)

    def color(self, row:int, intense:bool=False) -> Sequence[int]:
        """ Return an RGB 0-255 color tuple for a given row index and selection status. Use nesting depth as well. """
        return self.COLOR(1, self.depth, row, intense)


class SeparatorNode(GraphNode):
    """ The singular stroke separator has a special appearance.
        It is not connected to anything and has no owner, or is removed, depending on layout. """

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ The only primitive is a row substitution operation. """
        write(PrimitiveRowReplace(self.text), row, col)

    def connectors(self, *args) -> None:
        pass


class LeafNode(GraphNode):

    bottom_start: int = 0  # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.

    def __init__(self, shift:int, *args):
        super().__init__(*args)
        self.bottom_start = shift
        self.bottom_length -= shift

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ Write the main primitive: a text row starting at the origin with a shift to account for hyphens. """
        write(PrimitiveRow(self.text, self), row, col - self.bottom_start)


class UnmatchedNode(LeafNode):
    """ A set of unmatched keys. These have broken connectors ending in question marks on both sides. """

    TOP = PatternRow("¦")
    CUTOFF = PatternRow("?")

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ Add the body with an extra three-row offset to ensure that empty matches have enough space. """
        super().body(write, row + 3, col)

    def connectors(self, write:Callable, row:int, col:int, p_width:int) -> None:
        """ Draw top connectors downward and end in question marks just before reaching the bottom. """
        t_len = self.attach_length or 1
        b_len = self.bottom_length
        overhang = col - p_width + 1
        if overhang > 0:
            write(self.ENDPIECE(overhang), 0, col)
        for r in range(1, row - 1):
            write(self.TOP(t_len), r, col)
        write(self.CUTOFF(t_len), row - 1, col)
        write(self.CUTOFF(b_len), row + 1, col)
        write(self.TOP(b_len), row + 2, col)


class BranchNode(GraphNode):
    """ A pattern for important nodes with thicker connecting lines. """

    BOTTOM = PatternRow("║", "╠═╗")
    TOP = PatternRow("║", "╠═╝")
    CONNECTOR = PatternColumn("║")
    ENDPIECE = PatternRow("╗", "╦╦╗")

    def set_children(self, children:Sequence[GraphNode]):
        """ Set the list of children and propagate recursive attributes. """
        self.children = children
        for c in children:
            c.parent = self

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ Write the main primitive: a text row starting at the origin. """
        write(PrimitiveRow(self.text, self), row, col)


class InversionNode(BranchNode):
    """ Pattern for nodes describing an inversion of steno order. These show arrows to indicate reversal. """

    BOTTOM = PatternRow("║", "◄═►")


class RootNode(BranchNode):
    """ The root node always appears as a branch, even if it has no children. """

    COLOR = ClipMatrix([255, 0,   0,   0],  # It has a bright red color, or orange if selected.
                       [64,  0,   0,   100],
                       [64,  0,   0,   0])


class NodeFactory:

    _key_sep: str      # Steno key used as stroke separator.
    _key_split: str    # Steno key used to split sides in RTFCRE.
    _recursive: bool   # If True, also generate children of children (and so on).
    _rules_by_node: Dict[StenoRule, GraphNode]  # Mapping of each rule to its generated node.
    _nodes_by_rule: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.

    def __init__(self, key_sep:str, key_split:str, recursive:bool=True):
        self._key_sep = key_sep
        self._key_split = key_split
        self._recursive = recursive
        self._rules_by_node = {}
        self._nodes_by_rule = {}

    def __call__(self, rule:StenoRule) -> GraphNode:
        """ Generate a full output tree starting with the given rule as root.
            The root node has a depth of 0 and no parent, so its attach points are arbitrary. """
        return self._make_derived(rule)

    def _make_child(self, rule:StenoRule, *args) -> GraphNode:
        """ Only create derived type nodes if a rule has children and we are allowed to draw them. """
        if rule.rulemap and self._recursive:
            node = self._make_derived(rule, *args)
        else:
            node = self._make_base(rule, *args)
        # Keep track of the node and its rule in case we need one from the other.
        self._rules_by_node[rule] = node
        self._nodes_by_rule[node] = rule
        return node

    def _make_base(self, rule:StenoRule, *args) -> GraphNode:
        """ Base rules (i.e. leaf nodes) show their keys. """
        text = rule.keys
        if text == self._key_sep:
            return SeparatorNode(text, *args)
        elif RuleFlags.UNMATCHED in rule.flags:
            node_cls = UnmatchedNode
        else:
            node_cls = LeafNode
        # The text is shifted one to the right if the keys start with '-'.
        shift = (len(text) > 1 and text[0] == self._key_split)
        return node_cls(shift, text, *args)

    def _make_derived(self, rule:StenoRule, start:int=0, length:int=0, depth:int=0):
        """ Derived rules (i.e. branch nodes) show their letters and recursively add children from the rulemap. """
        text = rule.letters
        if not depth:
            node_cls = RootNode
        elif RuleFlags.INVERSION in rule.flags:
            node_cls = InversionNode
        else:
            node_cls = BranchNode
        node = node_cls(text, start, length, depth)
        child_depth = depth + 1
        node.set_children([self._make_child(i.rule, i.start, i.length, child_depth) for i in rule.rulemap])
        return node

    def rule_to_node(self, rule:StenoRule) -> Optional[GraphNode]:
        """ Given a rule, find the first node that used it (if any). """
        return self._rules_by_node.get(rule)

    def node_to_rule(self, node:GraphNode) -> Optional[StenoRule]:
        """ Given a node reference, look up its rule. """
        return self._nodes_by_rule.get(node)

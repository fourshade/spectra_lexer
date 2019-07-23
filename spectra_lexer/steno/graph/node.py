""" Module for higher-level text objects such as graph nodes for text operations. """

from typing import Callable, Dict

from .primitive import ClipMatrix, PatternColumn, PatternRow, PrimitiveRow, PrimitiveRowReplace
from spectra_lexer.resource import RuleFlags, StenoRule


class GraphNode:
    """ Abstract class representing a visible node in a tree structure of steno rules.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child list is mutable, hashing is by identity only. """
    COLOR = ClipMatrix([0,   64,  0,   -64],  # Vary red with nesting depth and selection (for purple),
                       [0,   0,   8,   100],  # vary green with the row index and selection,
                       [255, 0,   0,   0],    # starting from pure blue,
                       upper_bound=(192, 192, 255))  # and stopping short of invisible white.

    BOTTOM = PatternRow("│", "├─┐")    # Primitive constructor for the section above the text.
    TOP = PatternRow("│", "├─┘")       # Primitive constructor for the section below the text.
    CONNECTOR = PatternColumn("│")     # Primitive constructor for vertical connectors.
    ENDPIECE = PatternRow("┐", "┬┬┐")  # Primitive constructor for extension connectors.

    text: str           # Text characters drawn on the last row.
    attach_start: int   # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int  # Length of the attachment (may be different than its letters due to substitutions).
    bottom_length: int  # Length of the bottom attach point. Is the length of the text unless start is !=0.
    ref_str: str        # Unique reference string.
    parent = None       # Direct parent of the node. If None, it is the root node (or unconnected).
    children: list      # Direct children of the node.

    def __init__(self, text:str, start:int=0, length:int=1, parent=None, ref_str:str="#R"):
        """ A root node (default arguments) has a depth of 0 and no parent, so its attach points are arbitrary.
            It starts the reference chain with a base value, starting with a # for HTML anchor support. """
        self.text = text
        self.attach_start = start
        self.attach_length = length or 1
        self.bottom_length = len(text)
        self.parent = parent
        self.children = []
        self.ref_str = ref_str

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ Write the main primitive: a text row starting at the origin. """
        write(PrimitiveRow(self.text, self), row, col)

    def overhang(self, write:Callable, col:int, length:int) -> None:
        """ If the top container runs off the end, we need a corner ┐ endpiece. """
        write(self.ENDPIECE(length), 0, col)

    def connectors(self, write:Callable, row:int, col:int) -> None:
        """ Write connectors of a node at index <row, col>. The parent is by definition at row index 0. """
        # If there's a space available, add a bottom container ├--┐ next.
        if row > 2:
            write(self.BOTTOM(self.bottom_length), row - 1, col)
        # Add a top container ├--┘ near the parent. We always need this at minimum even with zero attach length.
        write(self.TOP(self.attach_length), 1, col)
        # If there's a gap, add a connector between the containers.
        gap_height = row - 3
        if gap_height > 0:
            write(self.CONNECTOR(gap_height), 2, col)

    @classmethod
    def color(cls, *args) -> str:
        """ Return an RGB color string for a given nesting depth, row index and selection status. """
        rgb = cls.COLOR(1, *args)
        return f'<span style="color:#{bytes(rgb).hex()};">{{}}</span>'

    @classmethod
    def bold(cls, selected:bool=False) -> str:
        """ Nodes are bold only when highlighted. """
        return '<b>{}</b>' if selected else "{}"

    def anchor(self) -> str:
        """ The anchor link is simply the ref string. """
        return f'<a href="{self.ref_str}">{{}}</a>'


class SeparatorNode(GraphNode):
    """ The singular stroke separator has a special appearance.
        It is not connected to anything and has no owner, or is removed, depending on layout. """

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ The only primitive is a row substitution operation. """
        write(PrimitiveRowReplace(self.text, self), row, col)

    def overhang(self, *args) -> None:
        pass

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
        super().body(write, row, col - self.bottom_start)


class UnmatchedNode(LeafNode):
    """ A set of unmatched keys. These have broken connectors ending in question marks on both sides. """

    TOP = PatternRow("¦")
    CUTOFF = PatternRow("?")

    def body(self, write:Callable, row:int=0, col:int=0) -> None:
        """ Add the body with an extra three-row offset to ensure that empty matches have enough space. """
        super().body(write, row + 3, col)

    def connectors(self, write:Callable, row:int, col:int) -> None:
        """ Draw top connectors downward and end in question marks just before reaching the bottom. """
        t_len = self.attach_length
        b_len = self.bottom_length
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

    @classmethod
    def bold(cls, selected:bool=False) -> str:
        """ Branch nodes are bold regardless of selection. """
        return super().bold(True)


class InversionNode(BranchNode):
    """ Pattern for nodes describing an inversion of steno order. These show arrows to indicate reversal. """

    BOTTOM = PatternRow("║", "◄═►")


class LinkedNode(BranchNode):
    """ Pattern for nodes describing two strokes linked together. """

    BOTTOM = PatternRow("♦", "♦═╗")
    TOP = PatternRow("♦", "♦═╝")
    CONNECTOR = PatternColumn("♦")


class RootNode(BranchNode):
    """ The root node always appears as a branch, even if it has no children. """

    COLOR = ClipMatrix([255, 0,   0,   0],  # It has a bright red color, or orange if selected.
                       [0,   0,   0,   120],
                       [0,   0,   0,   0])


class NodeFactory:

    _key_sep: str     # Steno key used as stroke separator.
    _key_split: str   # Steno key used to split sides in RTFCRE.

    def __init__(self, key_sep:str, key_split:str):
        self._key_sep = key_sep
        self._key_split = key_split

    def make_root(self, rule:StenoRule) -> RootNode:
        return RootNode(rule.letters)

    def make_base(self, rule:StenoRule, *args) -> GraphNode:
        """ Base rules (i.e. leaf nodes) show their keys. """
        text = rule.keys
        if text == self._key_sep:
            return SeparatorNode(text, *args)
        # The text is shifted one to the right if the keys start with '-'.
        shift = (len(text) > 1 and text[0] == self._key_split)
        if RuleFlags.UNMATCHED in rule.flags:
            return UnmatchedNode(shift, text, *args)
        else:
            return LeafNode(shift, text, *args)

    def make_derived(self, rule:StenoRule, *args) -> BranchNode:
        """ Derived rules (i.e. branch nodes) show their letters. """
        text = rule.letters
        flags = rule.flags
        if RuleFlags.INVERSION in flags:
            node_cls = InversionNode
        elif RuleFlags.LINKED in flags:
            node_cls = LinkedNode
        else:
            node_cls = BranchNode
        return node_cls(text, *args)


class NodeIndex:

    _rules_by_node: Dict[StenoRule, GraphNode]  # Mapping of each rule to its generated node.
    _nodes_by_rule: Dict[GraphNode, StenoRule]  # Mapping of each generated node to its rule.
    _anchors_by_node: Dict[str, GraphNode]      # Mapping of each generated node to its anchor ref string.

    def __init__(self):
        self._rules_by_node = {}
        self._nodes_by_rule = {}
        self._anchors_by_node = {}

    def add(self, node:GraphNode, rule:StenoRule) -> None:
        """ Keep track of nodes and rules in case we need one from the other, as well as the general anchor refs. """
        self._rules_by_node[rule] = node
        self._nodes_by_rule[node] = rule
        self._anchors_by_node[node.ref_str] = node

    def select_ref(self, ref:str=""):
        """ Return a node and corresponding rule to a reference string. """
        node = self._anchors_by_node.get(ref)
        selection = self._nodes_by_rule.get(node)
        return node, selection

    def select_rule(self, rule:StenoRule):
        """ Return a node corresponding to a rule, along with the rule itself if that node exists. """
        selection = None
        node = self._rules_by_node.get(rule)
        if node is not None:
            selection = rule
        return node, selection

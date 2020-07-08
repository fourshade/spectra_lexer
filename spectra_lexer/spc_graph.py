from collections import defaultdict
from typing import Container, Dict, Iterator, List, Mapping, Set

from spectra_lexer.graph import IBody, IConnectors, TextElement
from spectra_lexer.graph.body import BoldBody, SeparatorBody, ShiftedBody, StandardBody
from spectra_lexer.graph.canvas import GridCanvas
from spectra_lexer.graph.connectors import InversionConnectors, LinkedConnectors, NullConnectors, \
                                           SimpleConnectors, ThickConnectors, UnmatchedConnectors
from spectra_lexer.graph.format import HTMLFormatter
from spectra_lexer.graph.layout import CascadedGraphLayout, CompressedGraphLayout, GraphLayout, LayoutParams
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule

HTMLGraph = str                       # Marker type for an HTML text graph.
SuccessorsDict = Dict[int, Set[str]]  # Dictionary of a node's successor references by depth.
TextCanvas = GridCanvas[TextElement]  # Text graph element canvas.
EMPTY_ELEMENT = TextElement(" ")      # Blank text graph element with no markup or references.
RuleMapping = Mapping[str, StenoRule]
RuleDict = Dict[str, StenoRule]


class GraphNode:
    """ Represents a node in a tree structure of steno rules. Each node may have zero or more children. """

    _top = 0   # Current row for top of node body.
    _left = 0  # Current column for left side of node body.

    def __init__(self, ref:str, body:IBody, connectors:IConnectors,
                 tstart:int, tlen:int, children:List["GraphNode"]) -> None:
        self._ref = ref                # Reference string that is guaranteed to be unique in the tree.
        self._body = body              # The node's "body" containing steno keys or English text.
        self._connectors = connectors  # Pattern constructor for connectors.
        self._attach_start = tstart    # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen     # Length in characters of the attachment to the parent node.
        self._children = children      # List of direct children of this node.

    def move(self, row:int, col:int) -> None:
        """ Move the top-left corner of this node's body to <row, col>. """
        self._top = row
        self._left = col

    def layout(self, layout:GraphLayout) -> LayoutParams:
        """ Arrange each child node in rows and return the combined bounds. """
        # Minimum vertical spacing from the parent is determined by the connectors.
        top = self._connectors.min_height()
        # attach_start is the column index for the left side of the node body relative to the parent.
        left = self._attach_start
        # Our own node body is the smallest possible width and height.
        h = self._body.height()
        w = self._body.width()
        children = self._children
        if children:
            # Children are recursively laid out first to determine their height and width.
            params = [child.layout(layout) for child in children]
            # Arrange (or remove) children and calculate total width and height from the maximum child bounds.
            for child, output in zip(children[:], layout.arrange(params)):
                if output is None:
                    children.remove(child)
                else:
                    tb, lb, bb, rb = output
                    child.move(tb, lb)
                    if bb > h:
                        h = bb
                    if rb > w:
                        w = rb
        return top, left, h, w

    def _draw_normal(self, canvas:TextCanvas, top_row:int, bottom_row:int, col:int,
                     depth:int, successors:SuccessorsDict) -> None:
        """ Draw the text body and connectors (if any) on the canvas. """
        ref = self._ref
        for i in range(self._attach_length):
            successors[i+col].add(ref)
        body = self._body
        body_col = col + body.offset()
        text = body.text()
        bold_at = 1 - body.is_always_bold()
        for char in text:
            triggers = {ref, *successors[body_col]}
            elem = TextElement(char, ref, depth, bold_at, triggers)
            canvas.write(elem, bottom_row, body_col)
            body_col += 1
        height = bottom_row - top_row
        if height:
            triggers = {ref}.union(*successors.values())
            row = top_row
            for s in self._connectors.rows(height):
                c = col
                for char in s:
                    elem = TextElement(char, ref, depth, 100, triggers)
                    canvas.write(elem, row, c)
                    c += 1
                row += 1

    def _draw_sep(self, canvas:TextCanvas, row:int) -> None:
        """ Replace every element in the <row> with the separator. """
        text = self._body.text()
        elem = TextElement(text)
        canvas.replace_empty(elem, row)

    def draw(self, canvas:TextCanvas, parent_top=0, parent_left=0, depth=0) -> SuccessorsDict:
        """ Draw text elements on a canvas recursively from this node. """
        top = parent_top + self._top
        left = parent_left + self._left
        successors = defaultdict(set)
        # Reverse the composition order to ensure that the leftmost children get drawn last.
        for child in self._children[::-1]:
            triggers = child.draw(canvas, top, left, depth + 1)
            for i, s in triggers.items():
                successors[i].update(s)
        if self._body.is_separator():
            self._draw_sep(canvas, top)
        else:
            self._draw_normal(canvas, parent_top, top, left, depth, successors)
        return successors


class GraphTree(RuleMapping):
    """ A self-contained object to draw text graphs of a steno rule and optionally highlight any descendant.
        Implements the mapping protocol for ref strings to steno rules. """

    def __init__(self, root_rule:StenoRule, tree_map:RuleMapping, formatter:HTMLFormatter) -> None:
        self._root_rule = root_rule
        self._tree_map = tree_map
        self._formatter = formatter

    def __len__(self) -> int:
        return len(self._tree_map)

    def __iter__(self) -> Iterator[str]:
        return iter(self._tree_map)

    def __getitem__(self, k:str) -> StenoRule:
        """ Use the root node as a default. """
        return self._tree_map.get(k, self._root_rule)

    def draw(self, ref="", *, intense=False) -> HTMLGraph:
        """ Return an HTML text graph with <ref> highlighted.
            Highlight nothing if <ref> is blank. Use brighter highlighting colors if <intense> is True. """
        return self._formatter.format(ref, intense)


class GraphEngine:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, key_sep:str, ignored_chars:Container[str]) -> None:
        self._key_sep = key_sep        # Stroke separator key.
        self._ignored = ignored_chars  # Characters to ignore at the beginning of key strings (usually the hyphen).

    def _build_body(self, rule:StenoRule) -> IBody:
        """ Make a node display body. The text is shifted left if it starts with an ignored token. """
        keys = rule.keys
        if rule:
            body = BoldBody(rule.letters)
        elif keys == self._key_sep:
            body = SeparatorBody(keys)
        elif keys[:1] in self._ignored:
            body = ShiftedBody(keys, -1)
        else:
            body = StandardBody(keys)
        return body

    def _build_connectors(self, rule:StenoRule, length:int, width:int) -> IConnectors:
        """ Make a node connector set based on the rule type. """
        if rule.is_inversion:
            # Node for an inversion of steno order. Connectors should indicate some kind of "reversal".
            connectors = InversionConnectors(length, width)
        elif rule.is_linked:
            # Node for a child rule that uses keys from two strokes. This complicates stroke delimiting.
            connectors = LinkedConnectors(length, width)
        elif rule:
            connectors = ThickConnectors(length, width)
        elif rule.keys == self._key_sep:
            connectors = NullConnectors()
        elif rule.is_unmatched:
            connectors = UnmatchedConnectors(width)
        else:
            connectors = SimpleConnectors(length, width)
        return connectors

    def _build_tree(self, tree_map:RuleDict, rule:StenoRule, start:int, length:int) -> GraphNode:
        """ Build a display node tree recursively from a rule's properties, position, and descendants. """
        ref = str(len(tree_map))
        tree_map[ref] = rule
        children = [self._build_tree(tree_map, c.child, c.start, c.length) for c in rule]
        body = self._build_body(rule)
        width = body.width()
        connectors = self._build_connectors(rule, length, width)
        return GraphNode(ref, body, connectors, start, length, children)

    def graph(self, rule:StenoRule, *, compressed=True, compat=False) -> GraphTree:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        tree_map = {}
        root = self._build_tree(tree_map, rule, 0, len(rule.letters))
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        root.layout(layout)
        canvas = TextCanvas(EMPTY_ELEMENT)
        root.draw(canvas)
        grid = canvas.to_lists()
        formatter = HTMLFormatter(grid, compat=compat)
        return GraphTree(rule, tree_map, formatter)


def build_graph_engine(keymap:StenoKeyLayout) -> GraphEngine:
    key_sep = keymap.separator_key()
    ignored_chars = {keymap.divider_key()}
    return GraphEngine(key_sep, ignored_chars)

""" Main module for arranging text graph nodes on a character grid. """

from collections import defaultdict
from typing import Dict, Iterable, Iterator, List, Mapping, Sequence, Set, Tuple

from spectra_lexer.graph import IBody, IConnectors, TextElement
from spectra_lexer.graph.body import BoldBody, SeparatorBody, ShiftedBody, StandardBody
from spectra_lexer.graph.canvas import GridCanvas
from spectra_lexer.graph.connectors import InversionConnectors, LinkedConnectors, NullConnectors, \
                                           SimpleConnectors, ThickConnectors, UnmatchedConnectors
from spectra_lexer.graph.format import HTMLFormatter
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRule

SizeTuple = Tuple[int, int]
SuccessorsDict = Dict[int, Set[str]]
TextCanvas = GridCanvas[TextElement]  # Text graph element canvas.
EMPTY_ELEMENT = TextElement(" ")      # Blank text graph element with no markup or references.


class GraphNode:
    """ Represents a node in a tree structure of steno rules. Each node may have zero or more children. """

    ChildNodes = Sequence["GraphNode"]

    def __init__(self, ref:str, body:IBody, connectors:IConnectors,
                 tstart:int, tlen:int, children:ChildNodes) -> None:
        self._ref = ref                # Reference string that is guaranteed to be unique in the tree.
        self._body = body              # The node's "body" containing steno keys or English text.
        self._connectors = connectors  # Pattern constructor for connectors.
        self._attach_start = tstart    # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen     # Length in characters of the attachment to the parent node.
        self._children = children      # Direct children of this node.
        self._top = 0
        self._left = 0

    def min_row(self) -> int:
        """ Return the minimum row index to place the top of the node body relative to the parent.
            Minimum row spacing is determined by the connectors. """
        return self._connectors.min_height()

    def start_col(self) -> int:
        """ Return the column index to place the left side of the node body relative to the parent.
            This is also the relative start column index to highlight when this node is selected. """
        return self._attach_start

    def is_separator(self) -> bool:
        return self._body.is_separator()

    def body_size(self) -> SizeTuple:
        h = self._body.height()
        w = self._body.width()
        return h, w

    def move(self, row:int, col:int) -> None:
        self._top = row
        self._left = col

    def get_children(self) -> ChildNodes:
        return self._children

    def set_children(self, children:ChildNodes) -> None:
        self._children = children

    def _draw_normal(self, canvas:TextCanvas, top_row:int, bottom_row:int, col:int,
                     depth:int, successors:SuccessorsDict) -> None:
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
        for child in self._children:
            triggers = child.draw(canvas, top, left, depth + 1)
            for i, s in triggers.items():
                successors[i].update(s)
        if self.is_separator():
            self._draw_sep(canvas, top)
        else:
            self._draw_normal(canvas, parent_top, top, left, depth, successors)
        return successors


LayoutParams = Iterable[Tuple[GraphNode, SizeTuple]]
LayoutOutput = Iterator[Tuple[GraphNode, int, int]]


class BaseLayoutEngine:
    """ Abstract class for a text graph node layout engine. """

    def arrange_rows(self, params:LayoutParams) -> LayoutOutput:
        """ Lay out a series of nodes from <params> and yield each one with its final size.
            All row indices are relative to the parent node at index 0 and going down. """
        raise NotImplementedError

    def layout(self, node:GraphNode) -> SizeTuple:
        """ Arrange each child node in rows and return the combined size. """
        h, w = node.body_size()
        children = node.get_children()
        if not children:
            return h, w
        # Children are recursively laid out first to determine their height and width.
        params = [(child, self.layout(child)) for child in children]
        # Reverse the composition order to ensure that the leftmost objects get drawn last.
        new_children, heights, widths = zip(*self.arrange_rows(params))
        node.set_children(new_children[::-1])
        # Calculate total width and height from the maximum child bounds.
        # Our own node body will be the smallest possible width and height.
        return max([*heights, h]), max([*widths, w])


class CascadedLayoutEngine(BaseLayoutEngine):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def arrange_rows(self, params:LayoutParams) -> LayoutOutput:
        bottom_bound = 0
        right_bound = 0
        for node, size in params:
            height, width = size
            top_bound = node.min_row()
            left_bound = node.start_col()
            # Separators will never add extra rows.
            if node.is_separator():
                right_bound = 0
            # Move to the next free row, plus one more if this child shares columns with the last one.
            if top_bound < bottom_bound:
                top_bound = bottom_bound
            if right_bound > left_bound:
                top_bound += 1
            # Place the node and move down by a number of rows equal to its height.
            bottom_bound = top_bound + height
            right_bound = left_bound + width
            node.move(top_bound, left_bound)
            yield node, bottom_bound, right_bound


class CompressedLayoutEngine(BaseLayoutEngine):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows
        using a slot-based system. Each node records which row slot it occupies starting from the top down,
        and the rightmost column it needs. After that column passes, the slot becomes free again.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width   # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def arrange_rows(self, params:LayoutParams) -> LayoutOutput:
        last_row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for node, size in params:
            height, width = size
            top_bound = node.min_row()
            left_bound = node.start_col()
            # Separators are not drawn, but the first node after one must not line up with the previous.
            if node.is_separator():
                right_bound = self._max_width
                continue
            # If this node starts where the last one ended and there's no overlap, use the same row.
            if left_bound != right_bound or last_row < top_bound:
                # Search for the next free row from the top down and place the node there.
                for row in range(top_bound, self._max_height):
                    if slots[row] <= left_bound:
                        if height == 1 or all([b <= left_bound for b in slots[row+1:row+height]]):
                            last_row = row
                            break
                else:
                    # What monstrosity is this? Put the next row wherever.
                    last_row = top_bound
            top_bound = last_row
            bottom_bound = top_bound + height
            right_bound = left_bound + width
            # Prevent other text from starting adjacent to text in this node (unless handled specially as above).
            # Also prevent this node from overlapping the next with its connector (rare, but can happen with asterisks).
            new_slots = [*([left_bound + 1] * (top_bound - 1)),  # │... # . = free slots
                         right_bound,                            # ├┐.. # x = unavailable slots
                         *([right_bound + 1] * height),          # EUx. #
                         right_bound]                            # xx.. #
            # Only overwrite slots other nodes if ours is largest.
            for i, bound in enumerate(new_slots):
                if slots[i] < bound:
                    slots[i] = bound
            node.move(top_bound, left_bound)
            yield node, bottom_bound, right_bound


HTMLGraph = str  # Marker type for an HTML text graph.


class GraphTree(Mapping[str, StenoRule]):
    """ A self-contained object to draw text graphs of a steno rule and optionally highlight any descendant. """

    def __init__(self, tree_listing:Sequence[StenoRule], formatter:HTMLFormatter) -> None:
        self._tree_listing = tree_listing
        self._formatter = formatter

    def __len__(self) -> int:
        return len(self._tree_listing)

    def __iter__(self) -> Iterator[str]:
        """ Yield all ref strings to steno rules. """
        return map(str, range(len(self)))

    def __getitem__(self, k:str) -> StenoRule:
        return self._tree_listing[int(k)]

    def draw(self, ref="", *, intense=False) -> HTMLGraph:
        """ Return an HTML text graph with <ref> highlighted.
            Highlight nothing if <ref> is blank. Use brighter highlighting colors if <intense> is True. """
        return self._formatter.format(ref, intense)


class GraphEngine:
    """ Creates trees of displayable graph nodes out of steno rules. """

    def __init__(self, key_sep:str, ignored_chars="") -> None:
        self._key_sep = key_sep
        self._ignored = set(ignored_chars)  # Characters to ignore at the beginning of key strings (usually the hyphen).

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

    def _build_tree(self, tree_listing:List[StenoRule], rule:StenoRule, start:int, length:int) -> GraphNode:
        """ Build a display node tree recursively from a rule's properties, position, and descendants. """
        children = [self._build_tree(tree_listing, c.child, c.start, c.length) for c in rule]
        ref = str(len(tree_listing))
        tree_listing.append(rule)
        body = self._build_body(rule)
        width = body.width()
        connectors = self._build_connectors(rule, length, width)
        return GraphNode(ref, body, connectors, start, length, children)

    def graph(self, rule:StenoRule, *, compressed=True, compat=False) -> GraphTree:
        """ Generate a graph object for a steno rule.
            The root node's attach points are arbitrary, so start=0 and length=len(letters). """
        tree_listing = []
        root = self._build_tree(tree_listing, rule, 0, len(rule.letters))
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        h, w = layout_engine.layout(root)
        canvas = TextCanvas(h, w, EMPTY_ELEMENT)
        root.draw(canvas)
        grid = canvas.to_lists()
        formatter = HTMLFormatter(grid, compat=compat)
        return GraphTree(tree_listing, formatter)


def build_graph_engine(keymap:StenoKeyLayout) -> GraphEngine:
    key_sep = keymap.separator_key()
    ignored_chars = keymap.divider_key()
    return GraphEngine(key_sep, ignored_chars)

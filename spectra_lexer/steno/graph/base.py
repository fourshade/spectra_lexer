""" Base module for text graphing. Defines top-level graph structures. """

from collections import defaultdict
from functools import lru_cache
from typing import Iterator, List, Optional, Sequence, Tuple, Type

from .layout import BaseGraphLayout, CascadedGraphLayout, CompressedGraphLayout
from .render import BaseHTMLFormatter, Canvas, CompatHTMLFormatter, StandardHTMLFormatter
from .style import IConnectors, InversionConnectors, LinkedConnectors,\
    SimpleConnectors, ThickConnectors, UnmatchedConnectors


class GraphNode:
    """ A visible node in a tree structure of steno rules. Each node may have zero or more children. """

    _connector_cls: type  # Pattern constructor for connectors.

    def __init__(self, rule_name:str, text:str, tstart:int, tlen:int,
                 index:int, depth:int, children:Sequence) -> None:
        self._rule_name = rule_name  # Name of the rule from which this node was built.
        self._text = text            # Text characters drawn on the last row as the node's "body".
        self._attach_start = tstart  # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen   # Length in characters of the attachment to the parent node.
        self._index = index          # Unique tree index for this node.
        self._depth = depth          # Nesting depth of this node.
        self._children = children    # Direct children of this node.

    def ref(self) -> str:
        """ The reference string is the index; it is guaranteed to be unique in the tree. """
        return str(self._index)

    def rule_name(self) -> str:
        """ Return the name of the rule from which this node was built. """
        return self._rule_name

    def __iter__(self) -> Iterator:
        """ Yield all descendants of this node recursively depth-first. """
        yield self
        for child in self._children:
            yield from child

    def find_from_ref(self, ref:str) -> Optional:
        """ Return the child node with <ref> as its integer index. """
        try:
            return list(self)[int(ref)]
        except (IndexError, ValueError):
            return None

    def find_from_rule_name(self, rule_name:str) -> Optional:
        """ Return the first descendant node that matches <rule_name>, if any. """
        if self._rule_name == rule_name:
            return self
        for child in self._children:
            node = child.find_from_rule_name(rule_name)
            if node is not None:
                return node
        return None

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
        height = self._body_height()
        width = self._body_width()
        items = []
        children = self._children
        if children:
            child_params = []
            child_items = []
            for child in children:
                # Children are recursively laid out first to determine their height and width.
                mrow = child.min_row()
                mcol = child.min_col()
                h, w, c_items = child.layout(layout)
                child_params.append([mrow, mcol, h, w])
                child_items.append(c_items)
            bottom_bounds = [height]
            right_bounds = [width]
            bounds_iter = layout.arrange_rows(child_params)
            for child, c_items, (top, left, bottom, right) in zip(children, child_items, bounds_iter):
                if bottom > top or right > left:
                    items.append((child, top, left, c_items))
                    bottom_bounds.append(bottom)
                    right_bounds.append(right)
            # Reverse the composition order to ensure that the leftmost objects get drawn last.
            items.reverse()
            # Calculate total width and height from the maximum child bounds.
            height = max(bottom_bounds)
            width = max(right_bounds)
        return height, width, items

    def write(self, canvas:Canvas, top_row:int, bottom_row:int, col:int, intense:bool, target:Optional) -> None:
        is_colored = self._write_body(canvas, bottom_row, col, intense, target)
        height = bottom_row - top_row
        if height:
            self._write_connectors(canvas, top_row, col, height, intense, is_colored)

    def column_intersection(self, parent_start:int, parent_end:int):
        """ (parent_start, parent_end) is the index range for columns spanned by this node's parent.
            Return a new (equal or smaller) range of columns this child shares with it. """
        start = parent_start + self._attach_start
        end = min(parent_end, start + self._attach_length)
        return start, end

    def min_row(self) -> int:
        """ Return the minimum row index to place the node body relative to the parent. """
        raise NotImplementedError

    def min_col(self) -> int:
        """ Return the minimum (and currently, exact) column index to place the node body relative to the parent. """
        return self._attach_start

    def _body_height(self) -> int:
        """ Return the height of the node body in rows. """
        return 1

    def _body_width(self) -> int:
        """ Return the width of the node body in columns. """
        raise NotImplementedError

    def _write_body(self, canvas:Canvas, row:int, col:int, intense:bool, target:Optional) -> bool:
        """ Draw the text on the canvas. Return True if we colored at least part of it. """
        raise NotImplementedError

    def _write_connectors(self, canvas:Canvas, row:int, col:int, height:int, intense:bool, is_colored:bool) -> None:
        raise NotImplementedError


class SeparatorNode(GraphNode):
    """ The singular stroke separator is not connected to anything. It may be removed by the layout. """

    def min_row(self) -> int:
        return 0

    def _body_width(self) -> int:
        """ Separators go under everything else; they do not occupy any width on the layout. """
        return 0

    def _write_body(self, canvas:Canvas, row:int, *args) -> bool:
        """ Replace every space in <row> with the separator key using no markup. """
        assert len(self._text) == 1
        canvas.replace_empty(self._text, row)
        return False

    def _write_connectors(self, *args) -> None:
        pass


class ConnectedNode(GraphNode):

    _connector_cls: Type[IConnectors]

    def min_row(self) -> int:
        """ Default minimum spacing is 3 characters, or 2 if the body is one unit wide. """
        return 3 - (self._body_width() == 1)

    def _write_connectors(self, canvas:Canvas, row:int, col:int, height:int, intense:bool, is_colored:bool) -> None:
        """ Draw the connectors. Do *not* shift them. """
        ref = self.ref()
        connectors = self._connector_cls(self._attach_length, self._body_width()).strlist(height)
        for s in connectors:
            if is_colored:
                color = self._color(row, self._depth, intense)
                canvas.write_row(s, row, col, ref=ref, color=color)
            else:
                canvas.write_row(s, row, col, ref=ref)
            row += 1

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


class LeafNode(ConnectedNode):
    """ This node text may have an additional shift offset. """

    _connector_cls = SimpleConnectors

    _ignored = {'-'}  # Tokens to ignore at the beginning of key strings (usually the hyphen '-')

    def _body_width(self) -> int:
        """ The total width must account for the column shift. """
        return len(self._text) - self._is_shifted()

    def _is_shifted(self) -> bool:
        """ The text is shifted left if it starts with (and does not consist solely of) an ignored token. """
        text = self._text
        return bool(text and text[0] in self._ignored)

    def _write_body(self, canvas:Canvas, row:int, col:int, intense:bool, target:Optional) -> bool:
        """ Draw the text in a row after shifting to account for hyphens. """
        ref = self.ref()
        text = self._text
        col -= self._is_shifted()
        if target is self:
            color = self._color(row, self._depth, intense)
            canvas.write_row(text, row, col, ref=ref, color=color, bold=True)
            return True
        else:
            canvas.write_row(text, row, col, ref=ref)
            return False


class UnmatchedNode(LeafNode):

    _connector_cls = UnmatchedConnectors

    def min_row(self) -> int:
        """ The connectors require at least 6 characters to show the full gap. """
        return 6


class BranchNode(ConnectedNode):

    _connector_cls = ThickConnectors

    def _body_width(self) -> int:
        return len(self._text)

    def _write_body(self, canvas:Canvas, row:int, col:int, intense:bool, target:Optional) -> bool:
        # Write the non-formatted body first, then color only those columns shared with the terminal node.
        ref = self.ref()
        text = self._text
        canvas.write_row(text, row, col, ref=ref, bold=True)
        lineage = self.lineage(target) if target is not None else ()
        if not lineage:
            return False
        color = self._color(row, self._depth, intense)
        successors = lineage[1:]
        if successors:
            color_col_range = (0, 10000)
            for node in successors:
                color_col_range = node.column_intersection(*color_col_range)
            start, stop = color_col_range
            text = text[start:stop]
            col += start
        canvas.write_row(text, row, col, ref=ref, color=color, bold=True)
        return True


class InversionNode(BranchNode):

    _connector_cls = InversionConnectors


class LinkedNode(BranchNode):

    _connector_cls = LinkedConnectors


class StenoGraph:
    """ Formats and renders a monospaced text graph of a rule. """

    def __init__(self, root:GraphNode, layout:BaseGraphLayout, formatter:BaseHTMLFormatter):
        self._root = root
        self._layout = layout
        self._formatter = formatter  # Formats the output text based on which node is selected (if any).

    def find_node_from_ref(self, ref:str) -> Optional[GraphNode]:
        """ Return a reference node selected by anchor href. """
        ref = self._formatter.href_to_ref(ref)
        return self._root.find_from_ref(ref)

    def render(self, target:Optional[GraphNode], *, intense=False) -> str:
        """ Format a node graph and highlight a node ancestry line, starting with the root down to some terminal node.
            If <ancestry> is empty, highlight nothing. If <ancestry> is the root, highlight it (and only it) entirely.
            Otherwise, only highlight columns the root shares with the terminal node. """
        root = self._root
        height, width, items = root.layout(self._layout)
        canvas = Canvas(height, width, self._formatter)
        items = [(root, 0, 0, items)]
        self._render_recursive(canvas, 0, 0, items, target, intense)
        return str(canvas)

    def _render_recursive(self, canvas:Canvas, parent_row:int, parent_col:int,
                          items:List[tuple], target:Optional[GraphNode], intense:bool) -> None:
        """ Render each item on the canvas with respect to its parent. """
        for child, row, col, c_items in items:
            this_row = parent_row + row
            this_col = parent_col + col
            if c_items:
                self._render_recursive(canvas, this_row, this_col, c_items, target, intense)
            child.write(canvas, parent_row, this_row, this_col, intense, target)


class GraphEngine:
    """ Creates text graphs and fills indices matching these rules to their nodes. """

    def __init__(self) -> None:
        self._rules = {}
        self._connections = defaultdict(list)
        self._node_count = 0

    def _add_rule(self, name:str, text:str, node_cls:Type[GraphNode]) -> None:
        self._rules[name] = text, node_cls
        self._connections[name] = []

    def add_inversion_node(self, name:str, text:str) -> None:
        self._add_rule(name, text, InversionNode)

    def add_linked_node(self, name:str, text:str) -> None:
        self._add_rule(name, text, LinkedNode)

    def add_branch_node(self, name:str, text:str) -> None:
        self._add_rule(name, text, BranchNode)

    def add_separator_node(self, name:str, text:str) -> None:
        self._add_rule(name, text, SeparatorNode)

    def add_leaf_node(self, name:str, text:str) -> None:
        self._add_rule(name, text, LeafNode)

    def add_connection(self, parent:str, child:str, start:int, length:int) -> None:
        connections = self._connections[parent]
        connections.append((child, start, length))

    def make_tree(self, letters:str, connections:Sequence[Tuple[str, int, int]], unmatched_keys="") -> GraphNode:
        """ Make a graph tree from a lexer result and return the root node. """
        counter = iter(range(1, 10000))
        children = self._build_recursive(connections, 1, counter)
        root_length = len(letters)
        if unmatched_keys:
            last_match_end = 0 if not connections else sum(connections[-1][1:2])
            leftover_length = root_length - last_match_end
            node = UnmatchedNode("UNMATCHED", unmatched_keys, last_match_end, leftover_length, next(counter), 1, ())
            children.append(node)
        # The root node's attach points are arbitrary, so tstart=0 and tlen=blen.
        return BranchNode("ROOT", letters, 0, root_length, 0, 0, children)

    def make_graph(self, root:GraphNode, compressed=True, compat=False) -> StenoGraph:
        """ Make a graph object and formatter out of a <root> graph node.
            <compressed> - If True, lay out the graph in a manner that squeezes nodes together as much as possible.
            <compat> - If True, use a formatter that implements text monospacing with explicit markup. """
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        formatter = CompatHTMLFormatter() if compat else StandardHTMLFormatter()
        return StenoGraph(root, layout, formatter)

    def _build_recursive(self, connections:Sequence[Tuple[str, int, int]],
                         depth:int, counter:Iterator[int]) -> List[GraphNode]:
        """ Make a new graph node based on a rule's properties and/or child count. """
        nodes = []
        for name, start, length in connections:
            text, node_cls = self._rules[name]
            if not length:
                length = 1
            idx = next(counter)
            if name in self._connections:
                children = self._build_recursive(self._connections[name], depth + 1, counter)
            else:
                children = ()
            node = node_cls(name, text, start, length, idx, depth, children)
            nodes.append(node)
        return nodes

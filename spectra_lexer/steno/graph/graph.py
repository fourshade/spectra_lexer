""" Base module for text graphing. Defines top-level graph structures. """

from typing import Hashable, Iterable, Iterator, List, Optional, Sequence, Tuple, Type

from .layout import CascadedLayoutEngine, CompressedLayoutEngine, LayoutNode, GraphLayout
from .render import Canvas, CompatHTMLWriter, IMarkupWriter, StandardHTMLWriter
from .style import IConnectors, InversionConnectors, LinkedConnectors, \
    SimpleConnectors, ThickConnectors, UnmatchedConnectors

# Generic marker for the rule ID reference data type (may be anything hashable).
RULE_ID = Hashable


class GraphNode(LayoutNode):
    """ A visible node in a tree structure of steno rules. Each node may have zero or more children. """

    def __init__(self, rule_ids:List[RULE_ID],
                 text:str, caption:str, tstart:int, tlen:int, ref:str, depth:int, children:Sequence) -> None:
        self._rule_ids = rule_ids    # ID references to the rules from which this node was built.
        self._text = text            # Text characters drawn on the last row as the node's "body".
        self._caption = caption      # Text characters drawn as a caption (possibly on a tooltip).
        self._attach_start = tstart  # Index of the starting character in the parent node where this node attaches.
        self._attach_length = tlen   # Length in characters of the attachment to the parent node.
        self._ref = ref              # Unique reference string for this node.
        self._depth = depth          # Nesting depth of this node.
        self._children = children    # Direct children of this node.

    def ref(self) -> str:
        """ The reference string is guaranteed to be unique in the tree. """
        return self._ref

    def rule_ids(self) -> List[RULE_ID]:
        """ Return the IDs of the rules from which this node was built, if any. """
        return self._rule_ids

    def caption(self) -> str:
        """ Return a caption to display above the board diagram for various rules and lexer results. """
        return self._caption

    def lineage(self, node) -> Sequence:
        """ Return <node>'s ancestors in order, starting with self at index 0 and ending with <node>. """
        if node is self:
            return [self]
        for child in self._children:
            lineage = child.lineage(node)
            if lineage:
                return [self, *lineage]
        return ()

    def column_intersection(self, parent_start:int, parent_end:int):
        """ (parent_start, parent_end) is the index range for columns spanned by this node's parent.
            Return a new (equal or smaller) range of columns this child shares with it. """
        start = parent_start + self._attach_start
        end = min(parent_end, start + self._attach_length)
        return start, end

    def write(self, writer:IMarkupWriter, top_row:int, bottom_row:int, col:int, intense:bool, target:Optional) -> None:
        """ Draw the node onto a canvas in the given bounds. """
        raise NotImplementedError

    def children(self) -> Sequence["GraphNode"]:
        """ Return all direct children of this node. """
        return self._children

    def min_row(self) -> int:
        """ Default minimum spacing is 3 characters, or 2 if the body is one unit wide. """
        return 3 - (self.body_width() == 1)

    def min_col(self) -> int:
        """ Currently, attach_start is the exact column index to place the node body relative to the parent. """
        return self._attach_start

    def body_height(self) -> int:
        """ All node bodies are exactly one row of text. """
        return 1


class SeparatorNode(GraphNode):
    """ The singular stroke separator is not connected to anything. It may be removed by the layout. """

    def body_width(self) -> int:
        """ Separators go under everything else; they do not occupy any width on the layout. """
        return 0

    def is_separator(self) -> bool:
        return True

    def write(self, writer:IMarkupWriter, top_row:int, bottom_row:int, *args) -> bool:
        """ Replace every space in the bottom row with the separator key using no markup. """
        assert len(self._text) == 1
        writer.replace_empty(self._text, bottom_row)
        return False


class ConnectedNode(GraphNode):

    _connector_cls: Type[IConnectors]  # Pattern constructor for connectors.

    def write(self, writer:IMarkupWriter, top_row:int, bottom_row:int, col:int, intense:bool, target:Optional) -> None:
        is_colored = self._write_body(writer, bottom_row, col, intense, target)
        height = bottom_row - top_row
        if height:
            self._write_connectors(writer, top_row, col, height, intense, is_colored)

    def _write_body(self, writer:IMarkupWriter, row:int, col:int, intense:bool, target:Optional) -> bool:
        """ Draw the text body on the canvas. Return True if we colored at least part of it. """
        raise NotImplementedError

    def _write_connectors(self, writer:IMarkupWriter,
                          row:int, col:int, height:int, intense:bool, is_colored:bool) -> None:
        """ Draw the connectors. Do *not* shift them. """
        ref = self._ref
        bottom_length = self.body_width()
        connectors = self._connector_cls(self._attach_length, bottom_length).strlist(height)
        for s in connectors:
            if is_colored:
                color = self._color(row, intense)
                writer.write_row(s, row, col, ref=ref, color=color)
            else:
                writer.write_row(s, row, col, ref=ref)
            row += 1

    def _color(self, row:int, intense:bool) -> Tuple[int, int, int]:
        """ Return an RGB 0-255 color tuple based on a node's location and intensity. """
        # Start from pure blue. Add red with nesting depth, green with row index, and both with the intense flag.
        r = min(64 * self._depth - 64 * intense, 192)
        g = min(8 * row + 100 * intense, 192)
        b = 255
        return r, g, b


class LeafNode(ConnectedNode):
    """ This node text may have an additional shift offset. """

    _connector_cls = SimpleConnectors

    _ignored = {'-'}  # Tokens to ignore at the beginning of key strings (usually the hyphen '-')

    def body_width(self) -> int:
        """ The body width must account for the column shift. """
        return len(self._text) - self._is_shifted()

    def _is_shifted(self) -> bool:
        """ The text is shifted left if it starts with (and does not consist solely of) an ignored token. """
        text = self._text
        return bool(text and text[0] in self._ignored)

    def _write_body(self, writer:IMarkupWriter, row:int, col:int, intense:bool, target:Optional) -> bool:
        """ Draw the text in a row after shifting to account for hyphens. """
        ref = self._ref
        text = self._text
        col -= self._is_shifted()
        if target is self:
            color = self._color(row, intense)
            writer.write_row(text, row, col, ref=ref, color=color, bold=True)
            is_colored = True
        else:
            writer.write_row(text, row, col, ref=ref)
            is_colored = False
        return is_colored


class UnmatchedNode(LeafNode):

    _connector_cls = UnmatchedConnectors

    def min_row(self) -> int:
        """ The connectors require at least 6 characters to show the full gap. """
        return 6


class BranchNode(ConnectedNode):

    _connector_cls = ThickConnectors

    def body_width(self) -> int:
        return len(self._text)

    def _write_body(self, writer:IMarkupWriter, row:int, col:int, intense:bool, target:Optional) -> bool:
        # Write the non-formatted body first, then color only those columns shared with the terminal node.
        ref = self._ref
        text = self._text
        lineage = self.lineage(target) if target is not None else ()
        if not lineage:
            writer.write_row(text, row, col, ref=ref, bold=True)
            return False
        successors = lineage[1:]
        if successors:
            writer.write_row(text, row, col, ref=ref, bold=True)
            color_col_range = (0, 10000)
            for node in successors:
                color_col_range = node.column_intersection(*color_col_range)
            start, stop = color_col_range
            text = text[start:stop]
            col += start
        color = self._color(row, intense)
        writer.write_row(text, row, col, ref=ref, color=color, bold=True)
        return True


class InversionNode(BranchNode):
    """ Node for an inversion of steno order. Connectors should indicate some kind of "reversal". """

    _connector_cls = InversionConnectors


class LinkedNode(BranchNode):
    """ Node for a child rule that uses keys from two strokes. This complicates stroke delimiting. """

    _connector_cls = LinkedConnectors


class RootNode(BranchNode):

    def _color(self, row:int, intense:bool) -> Tuple[int, int, int]:
        """ The root node has a bright red color, or orange if selected. """
        return 255, 120 * intense, 0


class HTMLGraph:

    def __init__(self, root:GraphNode, layout:GraphLayout, *, compat=False) -> None:
        self._root = root
        self._layout = layout
        self._compat = compat

    def __iter__(self) -> Iterator[GraphNode]:
        """ Yield all descendants of the root recursively depth-first. """
        return self._iter(self._root)

    def _iter(self, node:GraphNode) -> Iterator[GraphNode]:
        yield node
        for child in node.children():
            yield from self._iter(child)

    def render(self, target:GraphNode=None, *, intense=False) -> str:
        """ Format a graph and highlight a node ancestry line down to some <target> node.
            If <target> is None, highlight nothing, otherwise highlight columns this node shares with <target>. """
        canvas = Canvas(self._layout.height(), self._layout.width())
        # If <compat> is True, use a formatter that implements text monospacing with explicit markup.
        writer = CompatHTMLWriter(canvas) if self._compat else StandardHTMLWriter(canvas)
        for child, parent_top, parent_left, top, left in self._layout:
            child.write(writer, parent_top, top, left, intense, target)
        return writer.join()


class GraphEngine:
    """ Formats and renders monospaced text graphs of rules. """

    def __init__(self) -> None:
        self._rule_data = {}         # Contains all parameters of each rule.
        self._rule_connections = {}  # Contains connections between each rule and its children.

    def add_rule(self, rule_id:RULE_ID, keys:str, letters="", desc="",
                 is_separator=False, is_inversion=False, is_linked=False) -> None:
        """ Add a new <rule_id> reference, which may be a string or any other hashable type. """
        self._rule_data[rule_id] = keys, letters, desc, is_separator, is_inversion, is_linked
        self._rule_connections[rule_id] = []

    def add_connection(self, parent:RULE_ID, child:RULE_ID, start:int, length:int) -> None:
        """ Add a connection between a <parent> and <child> rule.
            <start> - index of the character on the parent where the child starts its attachment.
            <length> - length of this attachment in characters, minimum 1. """
        self._rule_connections[parent].append((child, start, length or 1))

    def generate(self, letters:str, rule_ids:List[RULE_ID], rule_positions:List[int], unmatched_keys="",
                 compressed=False, compat=False) -> HTMLGraph:
        """ Make an HTML graph from a lexer result. """
        rule_lengths = [(len(self._rule_data[r][1]) or 1) for r in rule_ids]
        root_connections = zip(rule_ids, rule_positions, rule_lengths)
        counter = iter(range(1, 10000))
        children = self._build_recursive(root_connections, 1, counter)
        root_length = len(letters)
        if unmatched_keys:
            # The output is nowhere near reliable if some keys are unmatched.
            last_match_end = 0 if not rule_ids else (rule_positions[-1] + rule_lengths[-1])
            leftover_length = root_length - last_match_end
            caption = unmatched_keys + ": unmatched keys"
            node = UnmatchedNode([], unmatched_keys, caption, last_match_end, leftover_length,
                                 str(next(counter)), 1, ())
            children.append(node)
            if rule_ids:
                root_caption = "Incomplete match. Not reliable."
            else:
                root_caption = "No matches found."
        else:
            root_caption = "Found complete match."
        # The root node's attach points are arbitrary, so tstart=0 and tlen=blen.
        root = RootNode(rule_ids, letters, root_caption, 0, root_length, str(next(counter)), 0, children)
        # If <compressed> is True, lay out the graph in a manner that squeezes nodes together as much as possible.
        layout_engine = CompressedLayoutEngine() if compressed else CascadedLayoutEngine()
        layout = layout_engine.layout(root)
        return HTMLGraph(root, layout, compat=compat)

    def _build_recursive(self, connections:Iterable[Tuple[RULE_ID, int, int]],
                         depth:int, counter:Iterator[int]) -> List[GraphNode]:
        """ Make a new graph node based on a rule's properties and/or child count. """
        nodes = []
        for rule_id, start, length in connections:
            ref = str(next(counter))
            child_connections = self._rule_connections[rule_id]
            keys, letters, desc, is_separator, is_inversion, is_linked = self._rule_data[rule_id]
            # Base rules display only their keys to the left of their descriptions.
            caption = f"{keys}: {desc}"
            if child_connections:
                if letters:
                    # Derived rules show the complete mapping of keys to letters in their caption.
                    caption = f"{keys} → {letters}: {desc}"
                children = self._build_recursive(child_connections, depth + 1, counter)
                if is_inversion:
                    node = InversionNode([rule_id], letters, caption, start, length, ref, depth, children)
                elif is_linked:
                    node = LinkedNode([rule_id], letters, caption, start, length, ref, depth, children)
                else:
                    node = BranchNode([rule_id], letters, caption, start, length, ref, depth, children)
            else:
                if is_separator:
                    node = SeparatorNode([rule_id], keys, caption, start, length, ref, depth, ())
                else:
                    node = LeafNode([rule_id], keys, caption, start, length, ref, depth, ())
            nodes.append(node)
        return nodes

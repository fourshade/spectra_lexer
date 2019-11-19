""" Module for arranging text graph objects vertically on a character grid. """

from typing import Iterator, Sequence, Tuple


class LayoutNode:
    """ Interface for a text graph node that may be sized and laid out. """

    def children(self) -> Sequence["LayoutNode"]:
        """ Return all direct children of this node. """
        raise NotImplementedError

    def min_row(self) -> int:
        """ Return the minimum row index to place the top of the node body relative to the parent. """
        raise NotImplementedError

    def min_col(self) -> int:
        """ Return the minimum column index to place the left side of the node body relative to the parent. """
        raise NotImplementedError

    def body_height(self) -> int:
        """ Return the height of the node body in rows. """
        raise NotImplementedError

    def body_width(self) -> int:
        """ Return the width of the node body in columns. """
        raise NotImplementedError

    def is_separator(self) -> bool:
        return False


class GraphLayout:
    """ Finished text graph layout with renderable items in a list along with the total required canvas size. """

    # Contains a node, its position, and its parent's position: (child, parent_top, parent_left, this_top, this_left)
    Item = Tuple[LayoutNode, int, int, int, int]

    def __init__(self, height:int, width:int, items:Sequence[Item]) -> None:
        self._height = height  # Total height of the layout in rows.
        self._width = width    # Total width of the layout in columns.
        self._items = items    # Layout items in the order they should be drawn.

    def height(self) -> int:
        return self._height

    def width(self) -> int:
        return self._width

    def __iter__(self) -> Iterator[Item]:
        return iter(self._items)


class _LayoutResult:
    """ Recursive tree of layout results. Flattens into a list of usable graph layout items. """

    def __init__(self, node:LayoutNode, top:int, left:int, subresults:Sequence["_LayoutResult"]):
        self._node = node
        self._top = top
        self._left = left
        self._subresults = subresults

    def flatten(self, parent_top=0, parent_left=0) -> Sequence[GraphLayout.Item]:
        """ Position each item recursively with respect to its parent and return a flat item list. """
        items = []
        top = parent_top + self._top
        left = parent_left + self._left
        for result in self._subresults:
            items += result.flatten(top, left)
        items.append((self._node, parent_top, parent_left, top, left))
        return items


_NODE_PARAMS = Sequence[Tuple[LayoutNode, int, int]]


class BaseLayoutEngine:
    """ Abstract class for a text graph node layout engine. """

    def layout(self, root:LayoutNode) -> GraphLayout:
        """ Lay out <root> into a recursive tree of results, then flatten those into a list of drawable items. """
        height, width, results = self._layout(root)
        root_result = _LayoutResult(root, 0, 0, results)
        items = root_result.flatten()
        return GraphLayout(height, width, items)

    def _layout(self, node:LayoutNode) -> Tuple[int, int, Sequence[_LayoutResult]]:
        """ Arrange each child node in rows and return a nested sequence containing the nodes and their positions. """
        height = node.body_height()
        width = node.body_width()
        results = []
        children = node.children()
        if children:
            child_params = []
            child_items = []
            for child in children:
                # Children are recursively laid out first to determine their height and width.
                h, w, c_results = self._layout(child)
                child_params.append((child, h, w))
                child_items.append(c_results)
            bottom_bounds = [height]
            right_bounds = [width]
            bounds_iter = self._arrange_rows(child_params)
            for child, c_results, (top, left, bottom, right) in zip(children, child_items, bounds_iter):
                if bottom > top or right > left:
                    results.append(_LayoutResult(child, top, left, c_results))
                    bottom_bounds.append(bottom)
                    right_bounds.append(right)
            # Reverse the composition order to ensure that the leftmost objects get drawn last.
            results.reverse()
            # Calculate total width and height from the maximum child bounds.
            height = max(bottom_bounds)
            width = max(right_bounds)
        return height, width, results

    def _arrange_rows(self, node_params:_NODE_PARAMS) -> Iterator[Sequence[int]]:
        """ Lay out nodes using tuples of <node_params> and yield the row index for each.
            All row indices are relative to the parent node at index 0 and going down.
            If a node should not be displayed, yield None for its row index. """
        raise NotImplementedError


class CascadedLayoutEngine(BaseLayoutEngine):

    def _arrange_rows(self, node_params:_NODE_PARAMS) -> Iterator[Sequence[int]]:
        """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
            Recursive construction with one line per node means everything fits naturally with no overlap.
            Window space economy is poor (the triangle shape means half the space is wasted off the top).
            Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """
        bottom_bound = 0
        right_bound = 0
        for node, height, width in node_params:
            top_bound = node.min_row()
            left_bound = node.min_col()
            # Separators will never add extra columns.
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
            yield top_bound, left_bound, bottom_bound, right_bound


class CompressedLayoutEngine(BaseLayoutEngine):

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width   # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def _arrange_rows(self, node_params:_NODE_PARAMS) -> Iterator[Sequence[int]]:
        """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows
            using a slot-based system. Each node records which row slot it occupies starting from the top down,
            and the rightmost column it needs. After that column passes, the slot becomes free again.
            Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """
        last_row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for node, height, width in node_params:
            top_bound = node.min_row()
            left_bound = node.min_col()
            # Separators are not drawn, but the first node after one must not line up with the previous.
            if node.is_separator():
                yield top_bound, left_bound, top_bound, left_bound
                right_bound = self._max_width
                continue
            # If this node starts where the last one ended and there's no overlap, use the same row.
            if left_bound < right_bound or last_row < top_bound:
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
            slots[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            slots[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if slots[edge] < right_bound:
                    slots[edge] = right_bound
            yield top_bound, left_bound, bottom_bound, right_bound

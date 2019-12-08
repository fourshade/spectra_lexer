""" Module for arranging text graph objects vertically on a character grid. """

from typing import Iterable, Iterator, List, Tuple

from .base import GraphLayout, LayoutNode


class BaseLayoutEngine:
    """ Abstract class for a text graph node layout engine. """

    def layout(self, root:LayoutNode) -> GraphLayout:
        """ Lay out <root> into a recursive tree of drawable layouts. """
        height, width, sublayouts = self._layout(root)
        return GraphLayout(root, 0, 0, height, width, sublayouts)

    def _layout(self, node:LayoutNode) -> Tuple[int, int, List[GraphLayout]]:
        """ Arrange each child node in rows and return a nested sequence containing the nodes and their positions. """
        height = node.min_height()
        width = node.min_width()
        children = node.children()
        # Reverse the composition order to ensure that the leftmost objects get drawn last.
        sublayouts = [*self._arrange_rows(children)]
        sublayouts.reverse()
        # Calculate total width and height from the maximum child bounds.
        for layout in sublayouts:
            bottom = layout.bottom
            if bottom > height:
                height = bottom
            right = layout.right
            if right > width:
                width = right
        return height, width, sublayouts

    def _arrange_rows(self, nodes:Iterable[LayoutNode]) -> Iterator[GraphLayout]:
        """ Lay out a series of <nodes> and yield the layout for each.
            All row indices are relative to the parent node at index 0 and going down. """
        raise NotImplementedError


class CascadedLayoutEngine(BaseLayoutEngine):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def _arrange_rows(self, nodes:Iterable[LayoutNode]) -> Iterator[GraphLayout]:
        bottom_bound = 0
        right_bound = 0
        for node in nodes:
            top_bound = node.min_row()
            left_bound = node.start_col()
            # Children are recursively laid out first to determine their height and width.
            height, width, sublayouts = self._layout(node)
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
            yield GraphLayout(node, top_bound, left_bound, bottom_bound, right_bound, sublayouts)


class CompressedLayoutEngine(BaseLayoutEngine):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows
        using a slot-based system. Each node records which row slot it occupies starting from the top down,
        and the rightmost column it needs. After that column passes, the slot becomes free again.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width   # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def _arrange_rows(self, nodes:Iterable[LayoutNode]) -> Iterator[GraphLayout]:
        last_row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for node in nodes:
            top_bound = node.min_row()
            left_bound = node.start_col()
            # Children are recursively laid out first to determine their height and width.
            height, width, sublayouts = self._layout(node)
            # Separators are not drawn, but the first node after one must not line up with the previous.
            if node.is_separator():
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
            yield GraphLayout(node, top_bound, left_bound, bottom_bound, right_bound, sublayouts)

""" Module for arranging and rendering text graph objects into a character grid format. """

from typing import Iterable, Iterator, Sequence


class BaseGraphLayout:
    """ Abstract class for a text graph node layout engine. """

    def arrange_rows(self, node_params:Iterable[Sequence[int]]) -> Iterator[Sequence[int]]:
        """ Lay out nodes using tuples of <node_params> and yield the row index for each.
            All row indices are relative to the parent node at index 0 and going down.
            If a node should not be displayed, yield None for its row index. """
        raise NotImplementedError


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def arrange_rows(self, node_params:Iterable[Sequence[int]]) -> Iterator[Sequence[int]]:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        bottom_bound = 0
        right_bound = 0
        for top_bound, left_bound, height, width in node_params:
            # Separators will never add extra columns.
            if not width:
                right_bound = 0
            # Move to the next free row, plus one more if this child shares columns with the last one.
            if top_bound < bottom_bound:
                top_bound = bottom_bound
            if right_bound > left_bound:
                top_bound += 1
            bottom_bound = top_bound + height
            right_bound = left_bound + width
            yield top_bound, left_bound, bottom_bound, right_bound


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    _max_width = 50   # Graphs should never be wider than this many columns.
    _max_height = 50  # Graphs should never be taller than this many rows.

    def arrange_rows(self, node_params:Iterable[Sequence[int]]) -> Iterator[Sequence[int]]:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column passes, the slot becomes free again. """
        last_row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for top_bound, left_bound, height, width in node_params:
            # Separators are not drawn, but the first node after one must not line up with the previous.
            if not width:
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

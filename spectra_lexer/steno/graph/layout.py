""" Module for arranging and rendering text graph objects into a character grid format. """

from typing import Iterable


class BaseGraphLayout:
    """ Abstract class for a text graph node layout engine. """

    def arrange_rows(self, node_params:Iterable[list]) -> None:
        """ Lay out nodes using tuples of <node_params> and yield the row index for each.
            All row indices are relative to the parent node at index 0 and going down.
            If a node should not be displayed, yield None for its row index. """
        raise NotImplementedError


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def arrange_rows(self, node_params:Iterable[list]) -> None:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        row = 0
        right_bound = 0
        for params in node_params:
            min_row, start_col, height, width, *other = params
            # Move to the next free row, plus one more if this child shares columns with the last one.
            if row < min_row:
                row = min_row
            if right_bound > start_col and width:
                row += 1
            # Move the child to the current row and advance the bounds.
            params[0] = row
            row += height
            right_bound = start_col + width


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    _max_width = 50   # Graphs should never be wider than this many columns.
    _max_height = 50  # Graphs should never be taller than this many rows.

    def arrange_rows(self, node_params:Iterable[list]) -> None:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column passes, the slot becomes free again. """
        row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for params in node_params:
            min_row, start_col, height, width, *other = params
            # Separators will not enter the list.
            if not min_row:
                right_bound = self._max_width
                params[:] = ()
                continue
            # If this node starts where the last one ended and there's no overlap, use the same row.
            if start_col < right_bound or row < min_row:
                # Search for the next free row from the top down and place the node there.
                for r in range(min_row, self._max_height):
                    if slots[r] <= start_col:
                        if height == 1 or all([b <= start_col for b in slots[r+1:r+height]]):
                            row = r
                            break
                else:
                    # What monstrosity is this? Put the next row wherever.
                    row = min_row
            # Move the child to the current row and advance the bounds.
            params[0] = row
            top_bound = row
            bottom_bound = row + height
            right_bound = start_col + width
            slots[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            slots[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if slots[edge] < right_bound:
                    slots[edge] = right_bound

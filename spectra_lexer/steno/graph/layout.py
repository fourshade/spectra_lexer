from typing import Iterable, Iterator, Tuple


class BaseGraphLayout:
    """ Abstract class for a layout engine that arranges rows of graph nodes. """

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width    # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def layout_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[int]:
        """ Lay out nodes with <child_params> and yield their rows.
            Yield None instead if a child should not be included. """
        raise NotImplementedError


class CascadedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def layout_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[int]:
        """ Every time a new node is placed, we simply move down by a number of rows equal to its height. """
        bottom_bound = 0
        right_bound = 0
        for start_col, height, width, min_row in node_params:
            # Advance to the next free row. Move down one more if this child shares columns with the last one.
            row = bottom_bound or min_row
            if right_bound > start_col and width:
                row += 1
            # Place the child at the current position.
            yield row
            # Advance the bounds by the child's height and width.
            bottom_bound = row + height
            right_bound = start_col + width


class CompressedGraphLayout(BaseGraphLayout):
    """ Graph layout engine that attempts to arrange nodes and connections in the minimum number of rows.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def layout_rows(self, node_params:Iterable[Tuple[int, int, int, bool]]) -> Iterator[int]:
        """ Place nodes into rows using a slot-based system. Each node records which row slot it occupies starting from
            the top down, and the rightmost column it needs. After that column, the slot becomes free again. """
        top_bound = 0
        right_bound = 0
        bounds = [-1] * self._max_height
        for start_col, height, width, min_row in node_params:
            # Separators will not enter the row list.
            if not min_row:
                right_bound = self._max_width
                yield None
                continue
            # Make sure strokes don't run together.
            # If this node starts where the last one ended and there's no overlap, use the same row.
            row = top_bound
            if start_col < right_bound or row < min_row:
                # Search for the next free row from the top down and place the node there.
                for r in range(min_row, self._max_height):
                    if bounds[r] <= start_col:
                        if height == 1 or all([b <= start_col for b in bounds[r+1:r+height]]):
                            row = r
                            break
            # Place the child at the current position.
            yield row
            # Advance the bounds by the child's height and width.
            bottom_bound = row + height
            right_bound = start_col + width
            top_bound = row
            bounds[top_bound:bottom_bound] = [right_bound] * (bottom_bound - top_bound)
            # Prevent other text from starting adjacent to this text (unless handled specially as above).
            bounds[bottom_bound-1] = right_bound + 1
            # Make sure other nodes can't be placed directly above or below this one.
            # Only overwrite safety margins of other nodes if ours is larger.
            for edge in (top_bound - 1, bottom_bound):
                if bounds[edge] < right_bound:
                    bounds[edge] = right_bound

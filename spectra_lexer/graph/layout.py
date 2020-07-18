from typing import Iterable, Iterator, Optional, Tuple

LayoutParams = Tuple[int, int, int, int]            # input is mininum values for: (top, left, height, width).
LayoutBounds = Optional[Tuple[int, int, int, int]]  # output is final (top, left, bottom, right) bounds, or None.
LayoutIn = Iterable[LayoutParams]
LayoutOut = Iterator[LayoutBounds]


class GraphLayout:
    """ Abstract class for a text graph layout. """

    def arrange(self, params_iter:LayoutIn) -> LayoutOut:
        """ Lay out a series of items described by <params_iter> and yield the final bounds for each.
            All indices are relative to the parent at row 0 col 0, increasing going down and right.
            None may be returned as a value for the bounds, in which case that item should not be drawn. """
        raise NotImplementedError


class CascadedGraphLayout(GraphLayout):
    """ Graph layout that places nodes in descending order like a waterfall from the top down.
        Recursive construction with one line per node means everything fits naturally with no overlap.
        Window space economy is poor (the triangle shape means half the space is wasted off the top).
        Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate. """

    def arrange(self, params_iter:LayoutIn) -> LayoutOut:
        bottom_bound = 0
        right_bound = 0
        for top_bound, left_bound, height, width in params_iter:
            if not width:
                right_bound = 0
            # Move to the next free row, plus one more if this child shares columns with the last one.
            # Separators have no body width; these never need to move down an extra row.
            if top_bound < bottom_bound:
                top_bound = bottom_bound
            if width and right_bound > left_bound:
                top_bound += 1
            # Place the node and move down by a number of rows equal to its height.
            bottom_bound = top_bound + height
            right_bound = left_bound + width
            yield top_bound, left_bound, bottom_bound, right_bound


class CompressedGraphLayout(GraphLayout):
    """ Graph layout that attempts to arrange nodes and connections in the minimum number of rows using
        a slot-based system. Each node records which row slot it occupies starting from the top down,
        and the rightmost column it needs. After that column passes, the slot becomes free again.
        Since nodes belonging to different strokes may occupy the same row, no stroke separators are drawn. """

    def __init__(self, max_width=50, max_height=50) -> None:
        self._max_width = max_width    # Graphs should never be wider than this many columns.
        self._max_height = max_height  # Graphs should never be taller than this many rows.

    def arrange(self, params_iter:LayoutIn) -> LayoutOut:
        last_row = 0
        right_bound = 0
        slots = [-1] * self._max_height
        for top_bound, left_bound, height, width in params_iter:
            # Bodyless nodes are not drawn, but the first node after one must not line up with the previous.
            if not width:
                right_bound = self._max_width
                yield None
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
            yield top_bound, left_bound, bottom_bound, right_bound

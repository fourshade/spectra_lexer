from typing import List, Optional


class GridLocator:
    """ Simple indexer with bounds checking for objects in a list of lists with non-uniform lengths.
        The type of objects inside the lists does not matter; only the identity/reference matters.
        Works well for text graphs (which have a relatively small number of rows and columns compared to pixels). """

    _grid: List[list] = None  # List of lists of object references in [row][col] format.
    _last_obj: object = None  # Most recent object from a select event (for identity matching).

    def __init__(self, grid:List[list]):
        """ Save a 2D grid of object references from a new graph as a lookup table. """
        self._grid = grid

    def select(self, row:int, col:int) -> Optional:
        """ Return the object that was responsible for the graphical element at position (row, col).
            Return None if no element is there, no object owns the element, or an index is out of range. """
        if self._grid is None:
            return None
        if 0 <= row < len(self._grid):
            row = self._grid[row]
            if 0 <= col < len(row):
                return row[col]

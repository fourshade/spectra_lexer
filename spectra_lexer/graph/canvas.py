from typing import Generic, List, TypeVar

T = TypeVar("T")      # Element type.
Row_T = List[T]       # Mutable row of elements.
Grid_T = List[Row_T]  # Mutable grid of elements; a list of equal-length rows.


def grid_copy(grid:Grid_T) -> Grid_T:
    """ Copy a list of lists (but not the elements inside). """
    return list(map(list.copy, grid))


class GridCanvas(Generic[T]):
    """ Auto-expanding mutable 2D grid for drawing generic elements in a random-access manner. """

    def __init__(self, empty:T=None) -> None:
        self._empty = empty   # Empty grid element. Used for padding on expansion.
        self._grid = []       # Expandable element grid.
        self._nrows = 0       # Actual size of the grid in rows.
        self._ncols = 0       # Actual size of the grid in columns.
        self._row_offset = 0  # Offset in rows to add to every write command.
        self._col_offset = 0  # Offset in columns to add to every write command.

    def _blank_row(self, ncols:int) -> Row_T:
        """ Return a row of blank elements. """
        return [self._empty] * ncols

    def _blank_grid(self, nrows:int) -> Grid_T:
        """ Return a grid of blank elements. """
        r = self._blank_row(self._ncols)
        return grid_copy([r] * nrows)

    def _insert_rows(self, nrows:int) -> None:
        """ Pad the grid with empty rows at the top to allow writes at a negative index. """
        self._row_offset += nrows
        self._nrows += nrows
        self._grid[:0] = self._blank_grid(nrows)

    def _append_rows(self, nrows:int) -> None:
        """ Pad the grid with empty rows at the bottom. """
        self._nrows += nrows
        self._grid += self._blank_grid(nrows)

    def _adjusted_row(self, row:int) -> int:
        row += self._row_offset
        if row < 0:
            self._insert_rows(-row)
            row = 0
        if row >= self._nrows:
            self._append_rows(row - self._nrows + 1)
        return row

    def _insert_cols(self, ncols:int) -> None:
        """ Pad the grid with empty columns to the left to allow writes at a negative index. """
        self._col_offset += ncols
        self._ncols += ncols
        padding = self._blank_row(ncols)
        for r in self._grid:
            r[:0] = padding

    def _append_cols(self, ncols:int) -> None:
        """ Pad the grid with empty columns to the right. """
        self._ncols += ncols
        padding = self._blank_row(ncols)
        for r in self._grid:
            r += padding

    def _adjusted_col(self, col:int) -> int:
        col += self._col_offset
        if col < 0:
            self._insert_cols(-col)
            col = 0
        if col >= self._ncols:
            self._append_cols(col - self._ncols + 1)
        return col

    def write(self, element:T, row:int, col:int) -> None:
        """ Write an <element> to the grid at <row, col>. Expand to that size if it is out of bounds. """
        row = self._adjusted_row(row)
        col = self._adjusted_col(col)
        self._grid[row][col] = element

    def replace_empty(self, repl:T, row:int) -> None:
        """ Replace all empty elements in a entire row with <repl>. """
        row = self._adjusted_row(row)
        r = self._grid[row]
        for col, item in enumerate(r):
            if item is self._empty:
                r[col] = repl

    def to_lists(self) -> Grid_T:
        """ Return a copy of the current contents of the grid. """
        return grid_copy(self._grid)

    def __str__(self) -> str:
        """ Return all grid elements joined into a single string with default line ends. """
        sections = []
        for r in self._grid:
            sections += map(str, r)
            sections.append("\n")
        return "".join(sections)

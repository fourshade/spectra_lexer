from typing import List, Optional

from spectra_lexer.output.node import OutputNode


class NodeLocator:
    """ Simple implementation of an indexer with bounds checking for a list of lists with non-uniform lengths.
        Works well for text graphs (which have a relatively small number of rows and columns compared to pixels). """

    _node_grid: List[List[OutputNode]] = None  # List of lists of node references in [row][col] format.
    _last_node: OutputNode = None              # Most recent node from a select event (for identity matching).

    def __init__(self, node_grid:List[List[OutputNode]]):
        """ Save a 2D grid of node references from a new graph as a lookup table. """
        self._node_grid = node_grid

    def select_node_at(self, x:int, y:int) -> Optional[OutputNode]:
        """ Find the node owning the element at (x, y). Send the reference if it is different from last time. """
        node = self._lookup_node(x, y)
        if node is None or node is self._last_node:
            return None
        # Store the current node so we can avoid repeated lookups.
        self._last_node = node
        return node

    def _lookup_node(self, x:int, y:int) -> Optional[OutputNode]:
        """ Return the node that was responsible for the graphical element at position (x, y).
            Return None if no element is there, no node owns the element, or an index is out of range. """
        if self._node_grid is None:
            return None
        if 0 <= y < len(self._node_grid):
            node_row = self._node_grid[y]
            if 0 <= x < len(node_row):
                return node_row[x]

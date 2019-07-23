""" Module for the lowest-level string and list operations. Performance is more critical than readability here. """

from operator import itemgetter
from typing import List, Sequence


class Canvas(List[list]):
    """ A mutable 2D grid-like document structure that has metadata tag objects associated with strings.
        Each string should contain exactly one printable character, with additional optional markup.
        For performance, the implementation is low-level: each row is a list with alternating strings and tags.
        list.__init__ should not be overridden; this will facilitate fast list copying. No bounds checking is done.
        Operations on the document as a whole may span multiple rows, and should be optimized for map(). """

    # def memcpy(self, grid:List[list], row:int=0, col:int=0, _zip=zip, _len=len) -> None:
    #     """ Copy the contents of one grid directly to this one at the given offset. """
    #     col *= 2
    #     for r, line in _zip(self[row:], grid):
    #         r[col:col+_len(line)] = line
    #
    # def write_grid(self, grid:List[str], tag:object=None, row:int=0, col:int=0) -> None:
    #     """ Copy a grid of strings with a single tag to this one at the given offset. """
    #     for r, s in enumerate(grid, row):
    #         self.write_row(s, tag, r, col)

    def write_row(self, seq:Sequence[str], tag:object=None, row:int=0, col:int=0, _len=len) -> None:
        """ Writes a string <seq>uence with a single <tag> across a row with the top-left starting at <row, col>.
            This is the most performance-critical method in graphing, called hundreds of times per frame.
            Avoid method call overhead by inlining everything and using slice assignment over list methods. """
        r = self[row]
        col *= 2
        length = _len(seq)
        if length == 1:  # fast path: <s> contains one string.
            r[col:col+2] = [seq, tag]
            return
        length *= 2  # slow path: <s> is arbitrarily long.
        end = col + length
        r[col:end] = [tag] * length
        r[col:end:2] = seq

    def write_column(self, seq:Sequence[str], tag:object=None, row:int=0, col:int=0) -> None:
        """ Like write_row(), but writes the strings down a column instead of across a row.
            This is much slower because a different list must be accessed and written for every item. """
        col *= 2
        tag_col = col + 1
        for r, c in zip(self[row:], seq):
            r[col] = c
            r[tag_col] = tag

    @classmethod
    def blanks(cls, rows:int, cols:int):
        """ Make a new, blank grid of spaces and None references by copying a single line repeatedly with list(). """
        line = [" ", None] * cols
        return cls(map(list, [line] * rows))

    def row_replace(self, row:int, *args, _join="".join) -> None:
        """ Simulate a string replace operation on an entire row without altering any tags. """
        self[row][::2] = _join(self[row][::2]).replace(*args)

    def compile_strings(self, _chars=itemgetter(slice(0, None, 2))) -> List[List[str]]:
        """ De-interleave the string data from each row to form a list of lists or 2D grid of strings. """
        return list(map(_chars, self))

    def compile_tags(self, _tags=itemgetter(slice(1, None, 2))) -> List[list]:
        """ De-interleave the tag data from each row to form a list of lists or 2D grid of tags. """
        return list(map(_tags, self))

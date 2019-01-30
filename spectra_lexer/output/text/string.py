""" Module for the lowest-level string and list operations. Performance is more critical than readability here. """

from operator import itemgetter
from typing import List


class TaggedString(list):
    """ A mutable string-like structure that has a metadata tag object associated with each character.
        For performance, the implementation is low-level: a list with alternating characters and tags.
        list.__init__ should not be overridden; this will facilitate fast list copying. """

    _BLANKS_CACHE: dict = {}  # Cache of blank lines of various lengths for fast copying.

    def write(self, s:str, tag:object=None, start:int=0, _len=len) -> None:
        """ Overwrite characters with <s> and tags with <tag> starting at <start>. <s> may be another tagged string.
            This is the most performance-critical method in graphing, called hundreds of times per frame.
            Avoid method call overhead by inlining everything and using slice assignment over list methods. """
        start *= 2
        under = start - _len(self)
        if under > 0:  # if shorter than start position, pad with spaces and None tags.
            self.extend([" ", None] * (under // 2))
        length = _len(s)
        if length == 1:  # fast path: <s> is a one character string.
            self[start:start+2] = [s, tag]
            return
        length *= 2  # slow path: <s> is a arbitrarily long standard string.
        end = start + length
        self[start:end] = [tag] * length
        self[start:end:2] = s

    def memcpy(self, s:list, start:int=0, _len=len) -> None:
        """ Overwrite items directly with another tagged string. starting at <start>. """
        start *= 2
        under = start - _len(self)
        if under > 0:  # if shorter than start position, pad with spaces and None tags.
            self.extend([" ", None] * (under // 2))
        length = _len(s)
        self[start:start+length] = s

    @classmethod
    def from_string(cls, s:str="", tag:object=None, start:int=0, _len=len):
        """ Make a new object straight from a string without going through write(). Shifting works but is slow. """
        length = _len(s) * 2
        self = cls([tag] * length)
        self[:length:2] = s
        if start > 0:
            self[:] = ([" ", None] * start) + self
        return self

    @classmethod
    def blanks(cls, length:int, _cache_get=_BLANKS_CACHE.get):
        """ Make a new object consisting of repeated spaces and None references. These can be cached for speed. """
        result = _cache_get(length)
        if result is None:
            result = cls([" ", None] * length)
            cls._BLANKS_CACHE[length] = result
        return cls(result)

    def __str__(self, _join="".join) -> str:
        """ De-interleave the character data into a string. """
        return _join(self[::2])

    def tags(self) -> list:
        """ De-interleave the tag data into a list. """
        return self[1::2]

    def str_op(self, op:callable, *args) -> None:
        """ Do an in-place string operation without altering any tags. """
        self[::2] = op(str(self), *args)


class TaggedGrid(List[TaggedString]):
    """ List of tagged strings that form the lines of a full document. No bounds checking is done.
        Operations on the document as a whole may span multiple rows, and should be optimized for map(). """

    def memcpy(self, grid:List[list], row:int=0, col:int=0, _zip=zip, _len=len) -> None:
        """ Copy the contents of one grid directly to this one at the given offset. """
        col *= 2
        for r, line in _zip(self[row:], grid):
            r[col:col+_len(line)] = line

    def write(self, grid:List[str], tag:object=None, row:int=0, col:int=0, _zip=zip) -> None:
        """ Copy a list of strings with a single tag to this one at the given offset. """
        for r, s in _zip(self[row:], grid):
            r.write(s, tag, col)

    def write_row(self, s:str, tag:object=None, row:int=0, start_col:int=0) -> None:
        """ Like write(), but writes a single string and tag to any row in the grid.
            This should be relatively fast. """
        self[row].write(s, tag, start_col)

    def write_column(self, s:str, tag:object=None, start_row:int=0, col:int=0, _zip=zip) -> None:
        """ Like write(), but writes the string down a column instead of across a row.
            This is much slower because a different list must be accessed and written for every character. """
        col *= 2
        end_col = col + 2
        for r, c in _zip(self[start_row:], s):
            r[col:end_col] = [c, tag]

    @classmethod
    def blanks(cls, rows:int, cols:int):
        """ Make a new, blank grid of a given size. A cache is unnecessary due to rare use. """
        return cls(map(TaggedString.blanks, [cols] * rows))

    def size(self) -> tuple:
        """ Return the size of the grid in (rows, cols). Overall column size is determined by the longest one. """
        return len(self), max(map(len, self)) // 2

    def compile_strings(self, _chars=itemgetter(slice(0, None, 2)), _join="".join) -> List[str]:
        """ De-interleave the string data from each tagged string to form a list of strings. """
        return list(map(_join, map(_chars, self)))

    def compile_tags(self, _tags=itemgetter(slice(1, None, 2))) -> List[list]:
        """ De-interleave the tag data from each tagged string to form a list of lists or 2D grid of tags. """
        return list(map(_tags, self))

""" Module for rendering text graphs in grid form and formatting them into user-readable strings with markup. """

from typing import Iterable


class Canvas:
    """ A mutable 2D grid of strings for drawing text in a random-access manner.
        Each string should contain exactly one printed character, with additional optional markup. """

    def __init__(self, nrows:int, ncols:int, empty=" ") -> None:
        """ Make a new, blank grid by copying a single list repeatedly. """
        assert nrows > 0 and ncols > 0
        self._grid = [*map(list.copy, [[empty] * ncols] * nrows)]  # String data grid; a list of lists.
        self._empty = empty   # Empty grid character, also tested by identity for write changes.
        self._row_offset = 0  # Offset in rows to add to every write command.
        self._col_offset = 0  # Offset in columns to add to every write command.

    def write_row(self, seq:Iterable[str], row:int, col:int) -> None:
        """ Write a string <seq>uence across a row with the top-left starting at <row, col>. """
        row += self._row_offset
        if row < 0:
            self._shift_rows(-row)
            row = 0
        col += self._col_offset
        if col < 0:
            self._shift_cols(-col)
            col = 0
        r = self._grid[row]
        for s in seq:
            r[col] = s
            col += 1

    def replace_empty(self, char:str, row:int) -> None:
        """ Replace all uninitialized characters in a entire row with <char>. """
        row += self._row_offset
        r = self._grid[row]
        for col, item in enumerate(r):
            if item is self._empty:
                r[col] = char

    def _shift_rows(self, nrows:int) -> None:
        """ Pad the grid with rows at the top to compensate for an object drawing at a negative index. """
        self._row_offset += nrows
        ncols = len(self._grid[0])
        empty_row = [self._empty] * ncols
        self._grid[:0] = map(list.copy, [empty_row] * nrows)

    def _shift_cols(self, ncols:int) -> None:
        """ Pad the grid with columns to the left to compensate for an object drawing at a negative index. """
        self._col_offset += ncols
        padding = [self._empty] * ncols
        for r in self._grid:
            r[:0] = padding

    def join(self, row_delim="\n", col_delim="") -> str:
        """ Join the text grid into a single string. """
        line_iter = map(col_delim.join, self._grid)
        return row_delim.join(line_iter)

    __str__ = join  # str() returns the joined grid with default line ends.


class IMarkupWriter:
    """ Abstract canvas writer for text rows with markup. """

    def write_row(self, s:str, row:int, col:int, **markup) -> None:
        """ Format characters in a <s>tring with markup and write it to a canvas at <row, col>. """
        raise NotImplementedError

    def replace_empty(self, char:str, row:int) -> None:
        """ Replace all uninitialized characters in a entire row with <char> using no markup. """
        raise NotImplementedError


class BaseHTMLWriter(IMarkupWriter):
    """ Abstract canvas writer for HTML markup. Includes support for colors, boldface, and anchors. """

    # A style is required to stop anchors within the text from behaving as hyperlinks.
    ANCHOR_STYLE = '<style>.stenoGraph a {color: black; text-decoration: none;}</style>'
    PRE_HEADER = '<pre class="stenoGraph">'
    PRE_FOOTER = '</pre>'

    # HTML escape substitutions.
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

    def __init__(self, canvas:Canvas) -> None:
        self._canvas = canvas

    def write_row(self, s:str, row:int, col:int, ref="", bold=False, color:tuple=None) -> None:
        """ Format characters in a string with HTML tags. """
        text = []
        for char in s:
            if char in self._HTML_ESC:
                char = self._HTML_ESC[char]
            style = ""
            # Add a bold style if the node is important.
            if bold:
                style += 'font-weight:bold;'
            # Add an RGB color style if the node is highlighted.
            if color is not None:
                style += f'color:#{bytes(color).hex()};'
            # Wrap everything in an anchor tag with an href.
            # A # character is required to make it work properly in HTML anchor elements.
            text.append(f'<a href="#{ref}" style="{style}">{char}</a>')
        self._canvas.write_row(text, row, col)

    def replace_empty(self, char:str, *args) -> None:
        if char in self._HTML_ESC:
            char = self._HTML_ESC[char]
        self._canvas.replace_empty(char, *args)

    def join(self) -> str:
        """ Join text from the canvas into a single string. """
        raise NotImplementedError


class StandardHTMLWriter(BaseHTMLWriter):
    """ Formats text using preformatted tags with normal line breaks. """

    def join(self) -> str:
        """ Join the text grid as preformatted HTML. """
        headers = [self.ANCHOR_STYLE, self.PRE_HEADER]
        body = self._canvas.join()
        footers = [self.PRE_FOOTER]
        return "".join([*headers, body, *footers])


class CompatHTMLWriter(BaseHTMLWriter):
    """ Formats text using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts. """

    # Additional styles and tags needed for table elements.
    TABLE_STYLE = '<style>.stenoGraph td {padding: 0;}</style>'
    TABLE_HEADER = '<table style="border-spacing: 0"><tr><td>'
    TABLE_FOOTER = '</td></tr></table>'
    ROW_DELIM = '</td></tr><tr><td>'
    COL_DELIM = '</td><td>'

    def join(self) -> str:
        """ Join the text grid as an HTML table. """
        headers = [self.ANCHOR_STYLE, self.TABLE_STYLE, self.PRE_HEADER, self.TABLE_HEADER]
        body = self._canvas.join(self.ROW_DELIM, self.COL_DELIM)
        footers = [self.TABLE_FOOTER, self.PRE_FOOTER]
        return "".join([*headers, body, *footers])

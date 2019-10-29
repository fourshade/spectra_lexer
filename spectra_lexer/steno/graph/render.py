""" Module for rendering text graphs in grid form and formatting them into user-readable strings with markup. """

from typing import Iterable


class ICharFormatter:

    def format(self, char:str, **markup) -> str:
        """ Format a single character with markup and return it.
            This is a serious hotspot during graphing; avoid further method call overhead by inlining everything. """
        raise NotImplementedError

    def join_grid(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join each character of a string grid into a single string. """
        raise NotImplementedError


class BaseHTMLFormatter(ICharFormatter):
    """ Abstract formatter for text graphs with HTML markup. Includes support for colors, boldface, and anchors. """

    # A style is required to stop anchors within the text from behaving as hyperlinks.
    ANCHOR_STYLE = '<style>a.gg {color: black; text-decoration: none;}</style>'

    # HTML escape substitutions.
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

    def format(self, char:str, *, bold=False, color:tuple=None, ref:str=None) -> str:
        """ Format a <char>acter with HTML tags. """
        if char in self._HTML_ESC:
            char = self._HTML_ESC[char]
        # Add a bold style if the node is important.
        if bold:
            char = f'<b>{char}</b>'
        # Add an RGB color style if the node is highlighted.
        if color is not None:
            color_style = f'color:#{bytes(color).hex()};'
            char = f'<span style="{color_style}">{char}</span>'
        # Wrap everything in an anchor tag with an href.
        # A # character is required to make it work properly in HTML anchor elements.
        if ref is not None:
            char = f'<a class="gg" href="#{ref}">{char}</a>'
        return char


class StandardHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using preformatted tags with normal line breaks. """

    def join_grid(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join the text grid as preformatted HTML. """
        sections = [self.ANCHOR_STYLE, '<pre>']
        for row in grid:
            sections += row
            sections.append("\n")
        sections.append('</pre>')
        return "".join(sections)


class CompatHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts. """

    # Additional styles needed for table elements.
    TABLE_STYLE = '<style>td.tt {padding: 0;}</style>'

    def join_grid(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join the text grid as an HTML table. """
        sections = [self.ANCHOR_STYLE, self.TABLE_STYLE, '<pre><table style="border-spacing: 0">']
        for row in grid:
            sections.append('<tr>')
            for cell in row:
                sections += '<td class="tt">', cell, '</td>'
            sections.append('</tr>')
        sections.append('</table></pre>')
        return "".join(sections)


class Canvas:
    """ A mutable 2D grid of strings for drawing text in a random-access manner.
        Each string should contain exactly one printed character, with additional optional markup. """

    _empty = " "  # Empty grid character, also tested by identity for write changes.

    def __init__(self, nrows:int, ncols:int, formatter:ICharFormatter) -> None:
        """ Make a new, blank grid by copying a single list repeatedly. """
        self._grid = [*map(list.copy, [[self._empty] * ncols] * nrows)]  # String data grid; a list of lists.
        self._row_offset = 0  # Offset in rows to add to every write command (unused).
        self._col_offset = 0  # Offset in columns to add to every write command.
        self._formatter = formatter

    def write_row(self, seq:str, row:int, col:int, **markup) -> None:
        """ Write a character <seq>uence across a row with the top-left starting at <row, col>. """
        # row += self._row_offset
        col += self._col_offset
        if col < 0:
            self._shift_cols(-col)
            col = 0
        r = self._grid[row]
        fmt = self._formatter.format
        for char in seq:
            r[col] = fmt(char, **markup)
            col += 1

    def replace_empty(self, char:str, row:int, **markup) -> None:
        """ Replace all uninitialized characters in a entire row with <char>. """
        # row += self._row_offset
        r = self._grid[row]
        f_char = self._formatter.format(char, **markup)
        for col, item in enumerate(r):
            if item is self._empty:
                r[col] = f_char

    def _shift_cols(self, ncols:int) -> None:
        """ Pad the grid with columns to the left to compensate for an object attempting to draw at a negative index.
            Redirect drawing methods to draw relative to the the new zero point. """
        self._col_offset += ncols
        padding = [self._empty] * ncols
        for r in self._grid:
            r[:0] = padding

    def __str__(self) -> str:
        """ Return the text grid formatted as a string. """
        return self._formatter.join_grid(self._grid)

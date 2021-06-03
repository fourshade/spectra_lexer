""" HTML formatter for grids of text elements with markup. """

from functools import lru_cache
from typing import Sequence

from . import TextElement

TextElementGrid = Sequence[Sequence[TextElement]]  # Indexable 2D grid of text elements.


class HTMLFormat:
    """ Format parameters for HTML text graphs with CSS. """

    def __init__(self, header:str, footer:str, row_delim:str, cell_delim:str, stylesheet:str) -> None:
        self.header = header          # Header for each graph (not including CSS styles).
        self.footer = footer          # Footer for each graph (not including CSS styles).
        self.row_delim = row_delim    # Delimiter to place between each row.
        self.cell_delim = cell_delim  # Delimiter to place between each cell.
        self.stylesheet = stylesheet  # CSS stylesheet. Required to stop anchor hyperlink behavior at minimum.


# CSS class for the root HTML element in a finished graph.
ROOT_CSS_CLASS = "stenoGraph"

# Format using preformatted whitespace with normal line breaks.
# Adds additional styles needed for monospacing.
HTML_STANDARD = HTMLFormat(
    header=f'<div class="{ROOT_CSS_CLASS}">',
    footer='</div>',
    row_delim="\n",
    cell_delim="",
    stylesheet=f'.{ROOT_CSS_CLASS} {{white-space: pre;}} '
               f'.{ROOT_CSS_CLASS} a {{color: black; text-decoration: none;}} ')

# Format using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts.
# Adds additional styles needed for table elements.
HTML_COMPAT = HTMLFormat(
    header=f'<table class="{ROOT_CSS_CLASS}"><tr><td>',
    footer='</td></tr></table>',
    row_delim='</td></tr><tr><td>',
    cell_delim='</td><td>',
    stylesheet=f'.{ROOT_CSS_CLASS} {{white-space: pre; border-spacing: 0;}} '
               f'.{ROOT_CSS_CLASS} a {{color: black; text-decoration: none;}} '
               f'.{ROOT_CSS_CLASS} td {{padding: 0;}} ')


@lru_cache(maxsize=None)
def _color_style(row:int, index:int, intense:bool) -> str:
    """ Return an RGB 0-255 hex color style based on a node's location and intensity. """
    # Start from pure blue. Add red with nesting depth, green with row index, and both with the intense flag.
    if not index:
        # The root node has a bright red color, or orange if selected.
        r = 255
        g = 120 * intense
        b = 0
    else:
        r = min(64 * index - 64 * intense, 192)
        g = min(8 * row + 100 * intense, 192)
        b = 255
    return f'color:#{bytes([r, g, b]).hex()};'


class HTMLFormatter:
    """ Formatter for HTML text grids with CSS. Includes support for colors, boldface, and anchors. """

    # HTML escape substitutions.
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

    def __init__(self, grid:TextElementGrid, fmt:HTMLFormat) -> None:
        self._grid = grid  # Text elements to mark up, arranged in a grid for monospaced rendering.
        self._fmt = fmt    # Formatting parameters for rows, cells, etc.

    def format(self, target="", intense=False) -> str:
        """ Format grid elements into a full HTML graph with <target> highlighted. """
        fmt = self._fmt
        sections = ['<style>', fmt.stylesheet, '</style>', fmt.header]
        delim = fmt.cell_delim
        row = 0
        for r in self._grid:
            if r:
                for elem in r:
                    char = elem.char
                    if char in self._HTML_ESC:
                        char = self._HTML_ESC[char]
                    if not elem.ref:
                        new_sections = [char, delim]
                    else:
                        is_active = target in elem.activators
                        style = ""
                        # Add a bold style if the element allows it for this activity level.
                        if elem.bold_at <= is_active:
                            style += 'font-weight:bold;'
                        # Add an RGB color style if the element is highlighted.
                        if is_active:
                            style += _color_style(row, elem.color_index, intense)
                        # Wrap everything in an anchor tag with an href.
                        # A # character is required to make it work properly in HTML anchor elements.
                        new_sections = ['<a href="#', elem.ref, '" style="', style, '">', char, '</a>', delim]
                    sections += new_sections
                sections.pop()
            sections.append(fmt.row_delim)
            row += 1
        sections.append(fmt.footer)
        return "".join(sections)

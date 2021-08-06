""" HTML formatter for grids of text elements with markup. """

from functools import lru_cache
from typing import Container, Sequence


class TextElement:
    """ A single text element with markup. Corresponds to exactly one printed character. """

    __slots__ = ["char", "ref", "color_index", "bold_at", "activators"]

    def __init__(self, char:str, ref="", color_index=0, bold_at=10, activators:Container[str]=()) -> None:
        self.char = char                # Printed text character.
        self.ref = ref                  # Primary ref string - links to the node that was responsible for this element.
        self.color_index = color_index  # Numerical index to a table of RGB colors.
        self.bold_at = bold_at          # 0 = always bold, 1 = bold when activated, >1 = never bold.
        self.activators = activators    # Contains all refs that will activate (highlight) this element.


TextElementGrid = Sequence[Sequence[TextElement]]  # Indexable 2D grid of text elements for monospaced rendering.


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


_HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}  # HTML escape substitutions.


class HTMLFormatter:
    """ Formatter for HTML text grids with CSS. Includes support for colors, boldface, and anchors. """

    def __init__(self, *, header:str, footer:str, row_delim:str, cell_delim:str, stylesheet:str) -> None:
        self._header = header          # Header for each graph (not including CSS styles).
        self._footer = footer          # Footer for each graph (not including CSS styles).
        self._row_delim = row_delim    # Delimiter to place between each row.
        self._cell_delim = cell_delim  # Delimiter to place between each cell.
        self._stylesheet = stylesheet  # CSS stylesheet. Required to stop anchor hyperlink behavior at minimum.

    def format(self, grid:TextElementGrid, target="", *, intense=False) -> str:
        """ Format <grid> elements into a full HTML graph with <target> highlighted. """
        sections = ['<style>', self._stylesheet, '</style>', self._header]
        delim = self._cell_delim
        row = 0
        for r in grid:
            if r:
                for elem in r:
                    char = elem.char
                    if char in _HTML_ESC:
                        char = _HTML_ESC[char]
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
            sections.append(self._row_delim)
            row += 1
        sections.append(self._footer)
        return "".join(sections)


# CSS class for the root HTML element in a finished graph.
ROOT_CSS_CLASS = "stenoGraph"

# Formatter using preformatted whitespace with normal line breaks.
# Adds additional styles needed for monospacing.
HTML_STANDARD = HTMLFormatter(
    header=f'<div class="{ROOT_CSS_CLASS}">',
    footer='</div>',
    row_delim="\n",
    cell_delim="",
    stylesheet=f'.{ROOT_CSS_CLASS} {{display: inline-block; white-space: pre; cursor: pointer;}} '
               f'.{ROOT_CSS_CLASS} a {{color: black; text-decoration: none;}} ')

# Formatter using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts.
# Adds additional styles needed for table elements.
HTML_COMPAT = HTMLFormatter(
    header=f'<table class="{ROOT_CSS_CLASS}"><tr><td>',
    footer='</td></tr></table>',
    row_delim='</td></tr><tr><td>',
    cell_delim='</td><td>',
    stylesheet=f'.{ROOT_CSS_CLASS} {{display: inline-block; white-space: pre; cursor: pointer; border-spacing: 0;}} '
               f'.{ROOT_CSS_CLASS} a {{color: black; text-decoration: none;}} '
               f'.{ROOT_CSS_CLASS} td {{padding: 0;}} ')

""" Module for rendering text graphs in grid form and formatting them into user-readable strings with markup. """

from functools import lru_cache
from typing import List

from .base import TextElementGrid

GRAPH_CSS_CLASS = "stenoGraph"


class BaseHTMLFormatter:
    """ Abstract formatter for HTML text graphs with CSS. Includes support for colors, boldface, and anchors. """

    # HTML escape substitutions.
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

    # Header and footer for each graph (not including CSS styles).
    _header: str
    _footer: str

    # Delimiters for rows and columns.
    _row_delim: str
    _col_delim: str

    def __init__(self, grid:TextElementGrid) -> None:
        self._grid = grid

    def format(self, target="", intense=False) -> str:
        """ Format grid elements into a full HTML graph with <target> highlighted. """
        rd = self._row_delim
        cd = self._col_delim
        sections = ['<style>', *self._styles(), '</style>', self._header]
        row = 0
        for r in self._grid:
            if r:
                for elem in r:
                    char = elem.char
                    if char in self._HTML_ESC:
                        char = self._HTML_ESC[char]
                    if not elem.ref:
                        new_sections = [char, cd]
                    else:
                        is_active = target in elem.activators
                        style = ""
                        # Add a bold style if the element allows it for this activity level.
                        if elem.bold_at <= is_active:
                            style += 'font-weight:bold;'
                        # Add an RGB color style if the element is highlighted.
                        if is_active:
                            style += self._color_style(row, elem.color_index, intense)
                        # Wrap everything in an anchor tag with an href.
                        # A # character is required to make it work properly in HTML anchor elements.
                        new_sections = ['<a href="#', elem.ref, '" style="', style, '">', char, '</a>', cd]
                    sections += new_sections
                sections.pop()
            sections.append(rd)
            row += 1
        sections.append(self._footer)
        return "".join(sections)

    @staticmethod
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

    def _styles(self) -> List[str]:
        """ At least one style is required to stop anchors within the text from behaving as hyperlinks. """
        return [f'.{GRAPH_CSS_CLASS} a {{color: black; text-decoration: none;}} ']


class StandardHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using preformatted whitespace with normal line breaks. """

    _header = f'<div class="{GRAPH_CSS_CLASS}">'
    _footer = '</div>'

    _row_delim = "\n"
    _col_delim = ""

    def _styles(self) -> List[str]:
        """ Add additional styles needed for monospacing. """
        return [f'.{GRAPH_CSS_CLASS} {{white-space: pre;}} ',
                *super()._styles()]


class CompatHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts. """

    _header = f'<table class="{GRAPH_CSS_CLASS}"><tr><td>'
    _footer = '</td></tr></table>'

    _row_delim = '</td></tr><tr><td>'
    _col_delim = '</td><td>'

    def _styles(self) -> List[str]:
        """ Add additional styles needed for table elements. """
        return [f'.{GRAPH_CSS_CLASS} {{border-spacing: 0;}} ',
                f'.{GRAPH_CSS_CLASS} td {{padding: 0;}} ',
                *super()._styles()]

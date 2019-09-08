""" Module for formatting text graphs in grid form into user-readable strings with markup. """

from functools import lru_cache
from typing import Dict, Iterable, List

from .layout import BaseGraphLayout
from .render import GraphNode


class NodeAncestorDict(dict):
    """ Mapping of tree node-type objects to ordered sequences of their ancestors.
        At minimum, node objects must produce their children upon iteration.
        Each sequence contains one node for each level in the tree, starting with the root node at index 0. """

    def add(self, node:Iterable, *ancestors:Iterable) -> None:
        """ Add an entry for <node> matching it to its <ancestors>. The root node should have no ancestors at all.
            If there are children, add them recursively with <node> as the next ancestor in line. """
        self[node] = ancestors
        for child in node:
            self.add(child, *ancestors, node)


class BaseHTMLFormatter:
    """ Abstract formatter for text graphs with HTML markup. Includes support for anchors, colors, and boldface. """

    # ASCII character set and HTML escape substitutions.
    _ASCII = {*map(chr, range(32, 126))}
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}

    def __init__(self, chars:Iterable[List[str]], nodes:Iterable[List[GraphNode]], row_shift:int, col_shift:int,
                 ancestors:NodeAncestorDict, hrefs:Dict[GraphNode, str], rrefs:Dict[str, GraphNode]) -> None:
        self._chars = chars          # Root character grid to format.
        self._nodes = nodes          # Root node reference grid.
        self._row_shift = row_shift  # Row offset of the graph vs. the canvas.
        self._col_shift = col_shift  # Column offset of the graph vs. the canvas.
        self._ancestors = ancestors  # Mapping of nodes to sequences of their ancestors.
        self._hrefs = hrefs          # Mapping of each node to its anchor href string.
        self.get_node = rrefs.get    # Resolves a node reference from an href string.

    @classmethod
    def build(cls, root:GraphNode, layout:BaseGraphLayout):
        """ Render the root node, generate unique ref strings, and create a formatter with all generated resources.
            A # character is required to make ref strings work properly in HTML anchor elements. """
        canvas = layout.render(root)
        char_grid = canvas.chars()
        ref_grid = canvas.refs()
        row_shift, col_shift = canvas.get_offset()
        ancestors = NodeAncestorDict()
        ancestors.add(root)
        hrefs = {}
        rrefs = {}
        for i, node in enumerate(ancestors):
            href = f"#{i}"
            hrefs[node] = href
            rrefs[href] = node
        return cls(char_grid, ref_grid, row_shift, col_shift, ancestors, hrefs, rrefs)

    def to_html(self, node:GraphNode=None, intense:bool=False) -> str:
        """ Format a node graph and highlight a node ancestry line, starting with the root down to some terminal node.
            If <node> is None, highlight nothing. If <node> is the root, highlight it (and only it) entirely.
            Otherwise, only highlight columns the root shares with <node>. """
        root = None
        col_set = range(-10000, 10000)
        if node is None:
            ancestry = ()
        else:
            ancestry = *self._ancestors[node], node
            root, *others = ancestry
            start = self._col_shift
            for node in others:
                r = node.attach_range()
                col_set = {(i + start) for i in r if (i + start) in col_set}
                start += r.start
        ancestors_set = {*ancestry}
        depths = {node: i for i, node in enumerate(ancestry)}
        grid = [*map(list.copy, self._chars)]
        row = 0
        for nline in self._nodes:
            col = 0
            cline = grid[row]
            for node in nline:
                if node is not None:
                    highlighted = (node in ancestors_set and (node is not root or col in col_set))
                    char = cline[col]
                    # Only bother escaping and bolding ASCII characters.
                    if char in self._ASCII:
                        if char in self._HTML_ESC:
                            char = self._HTML_ESC[char]
                        # Most nodes are bold only when highlighted, but some are always bold.
                        if highlighted or node.bold():
                            char = f'<b>{char}</b>'
                    # Add an RGB color style if highlighted.
                    if highlighted:
                        color_style = self._color_style(depths[node], row, intense)
                        char = f'<span style="{color_style}">{char}</span>'
                    # Add everything to an anchor tag with the node's href string.
                    cline[col] = f'<a class="gg" href="{self._hrefs[node]}">{char}</a>'
                col += 1
            row += 1
        # Join and return the formatted grid. Add styles to stop anchors within the text from behaving as hyperlinks.
        return '<style>a.gg {color: black; text-decoration: none;}</style>' + self._join(grid)

    def _join(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join an entire grid of formatted text sections into a single string. """
        raise NotImplementedError

    @staticmethod
    @lru_cache(maxsize=None)
    def _color_style(depth:int, row:int, intense:bool) -> str:
        """ Return a CSS color style string from an RGB 0-255 color tuple based on a node's location and intensity. """
        if not depth:
            # The root node has a bright red color, or orange if selected.
            r = 255
            g = 120 if intense else 0
            b = 0
        else:
            # Start from pure blue. Add red with nesting depth, green with row index, and both with the intense flag.
            r = min(64 * (depth - intense), 192)
            g = min(8 * row + 100 * intense, 192)
            b = 255
        hex_color = bytes((r, g, b)).hex()
        return f'color:#{hex_color};'


class StandardHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using preformatted tags with normal line breaks. """

    def _join(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join a text grid as preformatted HTML. """
        text = ['<pre>']
        for row in grid:
            text += row
            text.append("\n")
        text.append('</pre>')
        return "".join(text)


class CompatHTMLFormatter(BaseHTMLFormatter):
    """ Formats text using explicit HTML tables. Useful for browsers that have trouble lining up monospace fonts. """

    def _join(self, grid:Iterable[Iterable[str]]) -> str:
        """ Join a text grid as an HTML table. Add additional styles for the table elements. """
        text = ['<style>td.tt {padding: 0;}</style>', '<pre><table style="border-spacing: 0">']
        for row in grid:
            text.append('<tr>')
            for cell in row:
                text += '<td class="tt">', cell, '</td>'
            text.append('</tr>')
        text.append('</table></pre>')
        return "".join(text)

from typing import Dict, List, Optional, Sequence, Tuple

from .render import GraphNode


class HTMLFormatter:
    """ Formats text lines with HTML markup. Includes support for anchors, colors, and boldface. """

    # ASCII character set and HTML escape substitutions.
    _ASCII = {*map(chr, range(32, 126))}
    _HTML_ESC = {"&": "&amp;", "<": "&lt;", ">": "&gt;"}
    # Styles to stop anchors within the block from behaving as hyperlinks.
    _HEADER = '<style>a.gg {color: black; text-decoration: none;}</style><pre>'
    _FOOTER = '</pre>'

    def __init__(self, char_grid:List[List[str]], node_grid:List[List[GraphNode]],
                 row_shift:int, col_shift:int, hrefs:Dict[GraphNode, str], rrefs:Dict[str, GraphNode]) -> None:
        self._char_grid = char_grid  # Root canvas of text to format.
        self._node_grid = node_grid  # Root canvas of nodes to format.
        self._row_shift = row_shift  # Row offset of the graph vs. the canvas.
        self._col_shift = col_shift  # Column offset of the graph vs. the canvas.
        self._hrefs = hrefs          # Mapping of each node to its anchor href string.
        self._rrefs = rrefs          # Mapping of each anchor href string to its node.

    def get_node(self, ref:str) -> Optional[GraphNode]:
        """ Return the node found by resolving the reference without the #. """
        return self._rrefs.get(ref[1:])

    def to_html(self, ancestry:Sequence[GraphNode]=(), intense:bool=False) -> str:
        """ Format a node graph and highlight a node ancestry line, starting with the root down to some terminal node.
            If there are no targets, highlight nothing. If there is only the root, highlight it (and only it) entirely.
            If there is more than one node, only highlight columns the root shares with descendants."""
        root = None
        col_set = range(0, 10000)
        if ancestry:
            root, *others = ancestry
            start = -self._col_shift
            for node in others:
                r = node.attach_range()
                col_set = {(i + start) for i in r if (i + start) in col_set}
                start += r.start
        ancestors_set = {*ancestry}
        depths = {node: i for i, node in enumerate(ancestry)}
        grid = [*map(list.copy, self._char_grid)]
        row = 0
        for nline in self._node_grid:
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
                    # Add RGB color tags if highlighted.
                    if highlighted:
                        rgb = self._rgb(depths[node], row, intense)
                        char = f'<span style="color:#{bytes(rgb).hex()};">{char}</span>'
                    # The anchor link is simply the ref string.
                    cline[col] = f'<a class="gg" href="#{self._hrefs[node]}">{char}</a>'
                col += 1
            row += 1
        return "\n".join([self._HEADER, *map(self.joined, grid), self._FOOTER])

    @staticmethod
    def _rgb(depth:int, row:int, intense:bool) -> Tuple[int, int, int]:
        """ Each RGB color is represented by a row of coefficients. The first is the starting value. """
        if not depth:
            # The root node has a bright red color, or orange if selected.
            return (255, 120, 0) if intense else (255, 0, 0)
        r = min(64 * (depth - intense), 192)  # Vary red with nesting depth and selection (for purple),
        g = min(8 * row + 100 * intense, 192)  # vary green with the row index and selection,
        b = 255  # Start from pure blue
        return r, g, b

    # Join and return a line with no modifications.
    joined = "".join


class CompatHTMLFormatter(HTMLFormatter):
    """ Formats text lines using explicit HTML tables for browsers that have trouble lining up monospace fonts. """

    _HEADER = HTMLFormatter._HEADER + '<style>td.tt {padding: 0;}</style><table style="border-spacing: 0">'
    _FOOTER = '</table>' + HTMLFormatter._FOOTER

    @staticmethod
    def joined(text_sections:list) -> str:
        """ Join and return a line as an HTML table row. """
        cells = [f'<td class="tt">{s}</td>' for s in text_sections]
        return f'<tr>{"".join(cells)}</tr>'

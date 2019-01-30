from collections import defaultdict
from functools import lru_cache
from typing import Dict, List, Sequence, Tuple

from spectra_lexer.output.node import OutputNode

# RGB 0-255 color tuples of the root node and starting color of other nodes when highlighted.
_ROOT_COLOR = (255, 64, 64)
_BASE_COLOR = (0, 0, 255)


def _rgb_color(level:int, row:int) -> Tuple[int, int, int]:
    """ Return an RGB 0-255 color tuple for any possible text row position and node depth. """
    if level == 0 and row == 0:
        return _ROOT_COLOR
    r, g, b = _BASE_COLOR
    r += min(192, level * 64)
    g += min(192, row * 8)
    return r, g, b


def _rgb_to_html(r:int, g:int, b:int) -> str:
    """ Return an HTML color string for a given RGB tuple. """
    return "#{0:02x}{1:02x}{2:02x}".format(r, g, b)


@lru_cache(maxsize=1024)
def _html_color(level:int, row:int) -> str:
    """ Return an HTML color string for a given text position and cache it. """
    return _rgb_to_html(*_rgb_color(level, row))


def _add_html(text:str, color:str, bold:bool) -> str:
    """ Format a string with HTML color and/or boldface. """
    text = """<span style="color:{0};">{1}</span>""".format(color, text)
    if bold:
        text = "<b>{}</b>".format(text)
    return text


def _format_interval(lines:List[str], level:int, row:int, start:int, end:int, bold:bool) -> None:
    """ Format a section of a row in a list of strings with HTML. """
    if start < end:
        line = lines[row]
        text = line[start:end]
        color = _html_color(level, row)
        text = _add_html(text, color, bold)
        lines[row] = "".join((line[:start], text, line[end:]))


class HTMLFormatter:
    """ Receives a list of text lines and instructions on formatting to apply in various places when any given
        node is highlighted. Creates structured text with explicit HTML formatting to be used by the GUI. """

    _lines: List[str]                                         # Lines containing the raw text.
    _format_dict: Dict[OutputNode, List[Tuple[int,int,int]]]  # Dict of special display info for each node.

    def __init__(self, lines:Sequence[str], node_grid:Sequence[Sequence[OutputNode]]):
        """ From a 2D node grid, compile a dict of nodes with ranges of character positions owned by each one. """
        self._lines = list(lines)
        self._format_dict = fd = defaultdict(list)
        for (row, node_row) in enumerate(node_grid):
            last_col = -1
            last_node = None
            for (col, node) in enumerate(node_row + [None]):
                if node is not last_node:
                    if last_node is not None:
                        fd[last_node].append((row, last_col, col))
                    last_col, last_node = col, node

    def make_graph_text(self, node:OutputNode=None) -> str:
        """ Make a full graph text string by joining the list of line strings and setting the preformatted tag.
            If a node is specified, format the lines with data corresponding to that node first. """
        if node is None:
            lines = self._lines
        else:
            lines = self._make_formatted_text(node)
        return "<pre>"+"\n".join(lines)+"</pre>"

    def _make_formatted_text(self, node:OutputNode) -> List[str]:
        """ Format the current set of text lines with highlighted and/or bolded ranges of text for a given node. """
        lines = self._lines[:]
        # Color the full ancestry line of the selected node, starting with that node and going up.
        # This ensures that formatting happens right-to-left on rows with more than one operation.
        nodes = node.get_ancestors()
        derived_start = sum(n.attach_start for n in nodes)
        derived_end = derived_start + node.attach_length
        level = len(nodes) - 1
        for n in nodes:
            rng_tuples = self._format_dict[n]
            # All of the node's characters above the text will be box-drawing characters.
            # These mess up when bolded, so only bold the last row (first in the reversed iterator).
            bold = True
            for (row, start, end) in reversed(rng_tuples):
                # If this is the last row of any ancestor node, only highlight the text our node derives from.
                if bold and n is not node:
                    start, end = derived_start, derived_end
                _format_interval(lines, level, row, start, end, bold)
                bold = False
            level -= 1
        return lines

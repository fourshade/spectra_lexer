from functools import lru_cache
from typing import List, Tuple

from spectra_lexer.interactive.graph.node import GraphNodeAppearance, TextNode
from spectra_lexer.interactive.graph.formatter import TextFormatter

# RGB 0-255 color tuples of the root node and starting color of other nodes when highlighted.
_ROOT_COLOR = (255, 64, 64)
_BASE_COLOR = (0, 0, 255)
# Format strings for HTML color, boldface, and full-text finishing style.
_COLOR_FORMAT = """<span style="color:#{0:02x}{1:02x}{2:02x};">{{}}</span>"""
_BOLD_FORMAT = "<b>{}</b>"
_FINISH_FORMAT = "<pre>{}</pre>"
# Columns to add to attach positions to account for <b>.
_ATTACH_COL_OFFSET = 3
# Appearance flags which dictate a default format for nodes, even if not selected.
# Every node with children is bold by default, as is the root.
_FORMAT_FLAGS = {GraphNodeAppearance.INVERSION: _BOLD_FORMAT,
                 GraphNodeAppearance.BRANCH:    _BOLD_FORMAT,
                 GraphNodeAppearance.ROOT:      _BOLD_FORMAT}


def _rgb_color(level:int, row:int) -> Tuple[int, int, int]:
    """ Return an RGB 0-255 color tuple for any possible text row position and node depth. """
    if level == 0 and row == 0:
        return _ROOT_COLOR
    r, g, b = _BASE_COLOR
    r += min(192, level * 64)
    g += min(192, row * 8)
    return r, g, b


@lru_cache(maxsize=None)
def _color_format(level:int, row:int) -> str:
    """ Return an HTML color format string for a specific position. """
    r, g, b = _rgb_color(level, row)
    return _COLOR_FORMAT.format(r, g, b)


class HTMLFormatter(TextFormatter):
    """ Receives a list of text lines and instructions on formatting to apply in various places when any given
        node is highlighted. Creates structured text with explicit HTML formatting to be used by the GUI. """

    _original_sections: List[List[str]]  # Original set of lines made at graph creation.

    def __init__(self, lines:List[str], node_grid:List[List[TextNode]]):
        """ From a 2D node grid, compile a dict of nodes with ranges of character positions owned by each one. """
        super().__init__(lines, node_grid)
        # Format the last section (i.e. the body) of every node with a special appearance and save it.
        for n in self:
            fmt = _FORMAT_FLAGS.get(n.appearance)
            if fmt is not None:
                section = self[n][-1][-1]
                self.format(section, fmt)
        self._original_sections = self.sections

    def make_graph_text(self, node:TextNode=None) -> str:
        """ Make a full graph text string by joining the list of section strings and setting the preformatted tag.
            If a node is specified, format the text with data corresponding to that node first. """
        if node is not None:
            # Restore the original state of each section first.
            self.sections = list(self._original_sections)
            self._format_node(node)
        return _FINISH_FORMAT.format(self.text())

    def _format_node(self, node:TextNode) -> None:
        """ Format the current text with highlights and/or bold for a given node. """
        # All of the node's characters above the text will be box-drawing characters.
        # These mess up when bolded, so only bold the last row, and only if it isn't bolded already.
        if _FORMAT_FLAGS.get(node.appearance) is not _BOLD_FORMAT:
            section = self[node][-1][-1]
            self.format(section, _BOLD_FORMAT)
        # Get the column positions of the node's original attach points.
        start = node.attach_start + _ATTACH_COL_OFFSET
        length = node.attach_length
        # Highlight the full ancestry line of the selected node.
        nodes = node.get_ancestors()
        level = len(nodes)
        for n in nodes:
            level -= 1
            indices = self[n][:]
            # For the last section of any ancestor node, only highlight the text our node derives from.
            if n is not node and indices:
                row, section = indices.pop()
                self.format_part(section, start, start + length, _color_format(level, row))
                start += n.attach_start
            # Highlight all other sections, which should only be box-drawing characters.
            for (row, section) in indices:
                self.format(section, _color_format(level, row))

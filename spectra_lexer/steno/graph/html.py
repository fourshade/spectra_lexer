from collections import defaultdict
from typing import Tuple

from .node import GraphNode
from .text import SectionedTextField
from spectra_lexer.utils import memoize

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
_FORMAT_FLAGS = defaultdict(tuple, {GraphNode.Appearance.INVERSION: (_BOLD_FORMAT,),
                                    GraphNode.Appearance.BRANCH:    (_BOLD_FORMAT,),
                                    GraphNode.Appearance.ROOT:      (_BOLD_FORMAT,)})


def _rgb_color(depth:int, row:int) -> Tuple[int, int, int]:
    """ Return an RGB 0-255 color tuple for any possible text row position and node depth. """
    if depth == 0:
        return _ROOT_COLOR
    r, g, b = _BASE_COLOR
    r += min(192, depth * 64)
    g += min(192, row * 8)
    return r, g, b


@memoize
def _color_format(depth:int, row:int) -> str:
    """ Return an HTML color format string for a specific position. """
    r, g, b = _rgb_color(depth, row)
    return _COLOR_FORMAT.format(r, g, b)


class HTMLTextField(SectionedTextField):
    """ Dictionary of text sections with instructions on formatting to apply in various places when any given
        node is highlighted. Creates structured text with explicit HTML formatting to be used by the GUI. """

    def start(self) -> None:
        """ Format the body of every node with a special appearance. """
        for n in self._ref_dict:
            for fmt in _FORMAT_FLAGS[n.appearance]:
                self._format_last_row(n, fmt)

    def _format_last_row(self, node:GraphNode, fmt:str) -> None:
        """ Format the last section (i.e. the body) of a node. """
        _, section_index = self._ref_dict[node][-1]
        self.format(section_index, fmt)

    def highlight(self, node:GraphNode, intense:bool=False) -> None:
        """ Format a copy of the current text with highlights and/or bold for a given node. """
        # All of the node's characters above the text will be box-drawing characters.
        # These mess up when bolded, so only bold the last section, and only if it isn't bolded already.
        if _BOLD_FORMAT not in _FORMAT_FLAGS[node.appearance]:
            self._format_last_row(node, _BOLD_FORMAT)
        # Get the column positions of the node's original attach points.
        start = node.attach_start + _ATTACH_COL_OFFSET
        length = node.attach_length
        # Highlight the full ancestry line of the selected node.
        for n in node.ancestors():
            indices = self._ref_dict[n][:]
            depth = n.depth * (1 + intense)
            # For the last section of any ancestor node, only highlight the text our node derives from.
            if n is not node and indices:
                self._highlight_sections([indices.pop()], depth, start, start + length)
                start += n.attach_start
            # Highlight all other sections, which should only be box-drawing characters.
            self._highlight_sections(indices, depth)

    def _highlight_sections(self, indices, depth:int, start:int=None, end:int=None) -> None:
        # Highlight all sections of a node, with an optional column range.
        for row, section_index in indices:
            self.format(section_index, _color_format(depth, row), start, end)

    def finish(self) -> str:
        """ Finish the text string by joining the list of section strings and setting the preformatted tag. """
        return _FINISH_FORMAT.format(self.to_string())

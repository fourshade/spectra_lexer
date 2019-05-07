from typing import Tuple

from .node import GraphNode, GraphNodeAppearance
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


@memoize
def _color_format(level:int, row:int) -> str:
    """ Return an HTML color format string for a specific position. """
    r, g, b = _rgb_color(level, row)
    return _COLOR_FORMAT.format(r, g, b)


class HTMLFormatter:
    """ Receives a list of text lines and instructions on formatting to apply in various places when any given
        node is highlighted. Creates structured text with explicit HTML formatting to be used by the GUI. """

    _sections: SectionedTextField  # Current working text sections.

    def __init__(self, sections:SectionedTextField):
        """ Format the last section (i.e. the body) of every node with a special appearance and save it. """
        for n in sections:
            fmt = _FORMAT_FLAGS.get(n.appearance)
            if fmt is not None:
                section = sections[n][-1][-1]
                sections.format(section, fmt)
        self._sections = sections

    def start(self) -> None:
        """ Save the current sections on the stack so we can reset them at the end. """
        self._sections.save()

    def highlight(self, node:GraphNode) -> None:
        """ Format a copy of the current text with highlights and/or bold for a given node. """
        # All of the node's characters above the text will be box-drawing characters.
        # These mess up when bolded, so only bold the last row, and only if it isn't bolded already.
        sections = self._sections
        if _FORMAT_FLAGS.get(node.appearance) is not _BOLD_FORMAT:
            section = sections[node][-1][-1]
            sections.format(section, _BOLD_FORMAT)
        # Get the column positions of the node's original attach points.
        start = node.attach_start + _ATTACH_COL_OFFSET
        length = node.attach_length
        # Highlight the full ancestry line of the selected node.
        nodes = list(node.ancestors())
        level = len(nodes)
        for n in nodes:
            level -= 1
            indices = sections[n][:]
            # For the last section of any ancestor node, only highlight the text our node derives from.
            if n is not node and indices:
                row, section = indices.pop()
                sections.format_part(section, start, start + length, _color_format(level, row))
                start += n.attach_start
            # Highlight all other sections, which should only be box-drawing characters.
            for row, section in indices:
                sections.format(section, _color_format(level, row))

    def finish(self) -> str:
        """ Finish the text string by joining the list of section strings and setting the preformatted tag.
            Restore the sections to their original state and return the finished text. """
        text = _FINISH_FORMAT.format(self._sections.to_string())
        self._sections.restore()
        return text

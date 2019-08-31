from .canvas import Canvas
from .node import GraphNode


class HTMLFormatter:
    """ Formats text lines with HTML markup. Includes support for anchors, colors, and boldface. """

    # Styles to stop anchors within the block from behaving as hyperlinks.
    _HEADER = '<style>a.gg {color: black; text-decoration: none;}</style><pre>'
    _FOOTER = '</pre>'

    def __init__(self, canvas:Canvas) -> None:
        self._canvas = canvas  # Root canvas of text to format.

    def to_html(self, target:GraphNode=None, intense:bool=False) -> str:
        """ Highlight the full ancestry line of the target node (if any), starting with itself up to the root. """
        if target is None:
            ancestors = cols = ()
        else:
            # For ancestors that are not the target object, only highlight the columns directly above the target.
            ancestors = set(target.ancestors())
            start = sum([node.attach_start for node in ancestors])
            cols = range(start, start + target.attach_length)
        formatted = []
        for row, line in enumerate(self._canvas):
            col = 0
            text = []
            it = iter(line)
            for char, node in zip(it, it):
                if node is not None:
                    char = node.format(char, node in ancestors and (node is target or col in cols), row, intense)
                text.append(char)
                col += 1
            formatted.append(self.joined(text))
        return "\n".join([self._HEADER, *formatted, self._FOOTER])

    # Join and return a line with no modifications.
    joined = "".join


class CompatFormatter(HTMLFormatter):
    """ Formats text lines using explicit HTML tables for browsers that have trouble lining up monospace fonts. """

    _HEADER = HTMLFormatter._HEADER + '<style>td.tt {padding: 0;}</style><table style="border-spacing: 0">'
    _FOOTER = '</table>' + HTMLFormatter._FOOTER

    @staticmethod
    def joined(text_sections:list) -> str:
        """ Join and return a line as an HTML table row. """
        cells = [f'<td class="tt">{s}</td>' for s in text_sections]
        return f'<tr>{"".join(cells)}</tr>'

from .canvas import Canvas
from .node import GraphNode
from .primitive import Primitive


class HTMLFormatter:
    """ Formats text lines with HTML markup. Includes support for anchors, colors, and boldface. """

    # Styles to stop anchors within the block from behaving as hyperlinks.
    _HEADER = '<style>a.gg {color: black; text-decoration: none;}</style><pre>'
    _FOOTER = '</pre>'

    _canvas: Canvas

    def __init__(self, root:Primitive, row:int=0, col:int=0) -> None:
        """ Render a root primitive onto a grid of minimum required size. Try again with a larger one if it fails. """
        s = row + col
        canvas = Canvas.blanks(root.height + s, root.width + s)
        try:
            root.write(canvas, row, col)
            self._canvas = canvas
        except ValueError:
            dim = s % 2
            self.__init__(root, row + dim, col + (not dim))

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
            for char, tag in zip(it, it):
                if tag is not None:
                    char = tag.format(char, tag in ancestors and (tag is target or col in cols), row, intense)
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

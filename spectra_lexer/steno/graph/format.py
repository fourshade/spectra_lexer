from .canvas import Canvas
from .node import GraphNode
from .primitive import BasePrimitive


class HTMLFormatter:
    """ Formats text lines with HTML markup. Includes support for anchors, colors, and boldface. """

    # Styles to stop anchors within the block from behaving as hyperlinks.
    _HEADER = '<style>a.gg {color: black; text-decoration: none;}</style><pre>'
    _FOOTER = '</pre>'

    def __init__(self, canvas:Canvas, row_shift=0, col_shift=0) -> None:
        self._canvas = canvas        # Root canvas of text to format.
        self._row_shift = row_shift  # Row offset of the graph vs. the canvas.
        self._col_shift = col_shift  # Column offset of the graph vs. the canvas.

    @classmethod
    def from_graph(cls, graph:BasePrimitive, row=0, col=0):
        """ Render the graph onto a grid of minimum required size. Try again with a larger one if it fails. """
        s = row + col
        canvas = Canvas.blanks(graph.height + s, graph.width + s)
        try:
            graph.write(canvas, row, col)
            return cls(canvas, row, col)
        except ValueError:
            dim = s % 2
            return cls.from_graph(graph, row + dim, col + (not dim))

    def to_html(self, target:GraphNode=None, intense:bool=False) -> str:
        """ Highlight the ancestry line of the target node (if any), starting with itself up to the root. """
        if target is None:
            # If there is no target, highlight nothing.
            def is_highlighted(node:GraphNode, col:int) -> bool:
                return False
        elif target.parent is None:
            # If the root node is the target, highlight it (and only it) entirely.
            def is_highlighted(node:GraphNode, col:int) -> bool:
                return node is target
        else:
            # If the root node is not the target, only highlight columns it shares with the target.
            # Highlight all non-root ancestors fully, including the target itself.
            *others, second, root = target.ancestors()
            start = self._col_shift + second.attach_start
            col_set = {*range(start, start + second.attach_length)}
            if others:
                start += sum([node.attach_start for node in others])
                col_set.intersection_update(range(start, start + target.attach_length))
            all_ancestors = {*others, second, root}
            def is_highlighted(node:GraphNode, col:int) -> bool:
                return node in all_ancestors and (node is not root or col in col_set)
        formatted = []
        for row, line in enumerate(self._canvas, -self._row_shift):
            col = 0
            text = []
            it = iter(line)
            for char, node in zip(it, it):
                if node is not None:
                    highlight = is_highlighted(node, col)
                    char = node.format(char, highlight, row, intense)
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

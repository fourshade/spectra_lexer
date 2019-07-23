from collections import defaultdict
import html
from typing import Dict, List, Tuple

from .canvas import Canvas
from .node import GraphNode
from .primitive import Primitive
from spectra_lexer.utils import traverse


class Formatter:
    """ Abstract base class for an HTML text block formatter. """

    def render(self, root:Primitive, row:int=0, col:int=0) -> Tuple[List[str], list]:
        """ Render a root primitive onto a grid of the minimum required size. Try again with a larger one if it fails.
            Return a list of standard strings and a grid with node references indexed by position. """
        s = row + col
        canvas = Canvas.blanks(root.height + s, root.width + s)
        try:
            root.write(canvas, row, col)
        except ValueError:
            dim = s % 2
            return self.render(root, row + dim, col + (not dim))
        return canvas.compile_strings(), canvas.compile_tags()


class HTMLFormatter(Formatter):
    """ Generates text lines with explicit HTML formatting. Each is divided into sections based on ownership.
        The main list is indexed by section. Each section is owned by a single object, and is formatted as a whole.
        Each row is terminated by an unowned newline section. Joining all sections produces the final text.
        Includes a dictionary of info to help apply formatting for any given node when highlighted. """

    # Styles to stop anchors within the block from behaving as hyperlinks.
    _HEADER = '<style>pre > a {color: black; text-decoration: none;}</style><pre>'
    _FOOTER = '</pre>'

    _sections: List[str]           # List of text sections based on ownership.
    _nodes: Dict[GraphNode, list]  # Node references each mapped to a list of (row, section) indices that node owns.

    def __init__(self, layout:Primitive):
        """ From a 2D reference grid and corresponding list of character strings, find contiguous ranges of characters
            owned by a single reference and create a section for each of them. Add each section of characters to the
            main list and record the row number and section index in the dict under the owner reference. """
        lines, ref_grid = self.render(layout)
        sections = self._sections = []
        sections_append = sections.append
        nodes = self._nodes = defaultdict(list)
        row = 0
        for chars, refs in zip(lines, ref_grid):
            last_col = 0
            last_ref, *refs = *refs, None
            for col, ref in enumerate(refs, 1):
                if ref is not last_ref:
                    if last_ref is not None:
                        nodes[last_ref].append((row, len(sections)))
                    sections_append(chars[last_col:col])
                    last_col, last_ref = col, ref
            sections_append("\n")
            row += 1

    def to_html(self, target:GraphNode=None, intense:bool=False) -> str:
        """ Render the graph inside preformatted tags, escaping, coloring and bolding nodes that require it.
            Highlight the full ancestry line of the target node (if any), starting with itself up to the root. """
        str_ops = [[] for _ in self._sections]
        for node, sections in self._nodes.items():
            # Escaping is expensive. Only escape those strings which originate with the user.
            # Both branch nodes and the selected node itself (if it is not a branch) are bolded after that.
            _, sect = sections[-1]
            str_ops[sect] = [html.escape, node.bold(node is target).format]
        if target is not None:
            ladder = list(traverse(target, "parent"))
            depths = range(len(ladder))[::-1]
            start = 0
            length = target.attach_length
            for node, depth in zip(ladder, depths):
                # For nodes that are ancestors of the selected node, add color tags first.
                sections = self._nodes[node]
                for row, sect in sections:
                    str_ops[sect].append(node.color(depth, row, intense).format)
                # It is rare, but possible to have a node with no sections, so test for that.
                if node is not target and sections:
                    # For ancestors that are not the target object, only highlight the part directly above the target.
                    _, sect = sections[-1]
                    def format_part(text:str, start=start, end=start+length, fmts=str_ops[sect]):
                        *fmts, color = fmts
                        pfx, body, sfx = [_apply(fmts, s) for s in (text[:start], text[start:end], text[end:])]
                        return f"{pfx}{color(body)}{sfx}"
                    str_ops[sect] = [format_part]
                # Add the attach start offset for each node as we climb the ladder.
                start += node.attach_start
        for node in self._nodes:
            # All non-empty nodes have anchor tags.
            a_fmt = node.anchor().format
            for _, sect in self._nodes[node]:
                str_ops[sect].append(a_fmt)
        # Apply format strings for every section in the order they were added and join them.
        return "".join([self._HEADER, *map(_apply, str_ops, self._sections), self._FOOTER])


def _apply(fns, text:str) -> str:
    for fn in fns:
        text = fn(text)
    return text

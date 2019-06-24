import html
from collections import defaultdict
from typing import Dict, List, Optional

from spectra_lexer.utils import traverse
from .node import GraphNode

_HEADER = '<style>.graph > a {color: black; text-decoration: none;}</style><pre class="graph">'
_FOOTER = '</pre>'


class HTMLTextField(List[str]):
    """ A list of text lines with explicit HTML formatting. Each is divided into sections based on ownership.
        The list is indexed by section only. Each section is owned by a single object, and is formatted as a whole.
        Each row is terminated by an unowned newline section. Joining all sections produces the final text.
        Includes a dictionary of info to help apply formatting for any given node when highlighted. """

    _ref_list: List[GraphNode]        # List of all node references in order of first appearance.
    _ref_dict: Dict[GraphNode, list]  # Node references each mapped to a list of (row, section) indices that node owns.

    def __init__(self, lines:List[str], ref_grid:List[List[GraphNode]]):
        """ From a 2D reference grid and corresponding list of character strings, find contiguous ranges of characters
            owned by a single reference and create a section for each of them. Add each section of characters to the
            main list and record the row number and section index in the dict under the owner reference. """
        super().__init__()
        append = self.append
        ref_dict = self._ref_dict = defaultdict(list)
        row = 0
        for chars, refs in zip(lines, ref_grid):
            last_col = 0
            last_ref, *refs = *refs, None
            for col, ref in enumerate(refs, 1):
                if ref is not last_ref:
                    if last_ref is not None:
                        ref_dict[last_ref].append((row, len(self)))
                    append(chars[last_col:col])
                    last_col, last_ref = col, ref
            append("\n")
            row += 1
        self._ref_list = list(ref_dict)

    def to_html(self, target:GraphNode=None, intense:bool=False) -> str:
        """ Render the graph inside preformatted tags, escaping, coloring and bolding nodes that require it.
            Highlight the full ancestry line of the target node (if any), starting with itself up to the root. """
        str_ops = [[] for _ in range(len(self))]
        for node in self._ref_list:
            # Escaping is expensive. Only escape those strings which originate with the user.
            # Both branch nodes and the selected node itself (if it is not a branch) are bolded after that.
            _, sect = self._ref_dict[node][-1]
            str_ops[sect] = [html.escape, node.bold(node is target).format]
        if target is not None:
            ladder = list(traverse(target, "parent"))
            depths = range(len(ladder))[::-1]
            start = 0
            length = target.attach_length
            for node, depth in zip(ladder, depths):
                # For nodes that are ancestors of the selected node, add color tags first.
                sections = self._ref_dict[node]
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
        for index, node in enumerate(self._ref_list):
            # All non-empty nodes have anchor tags.
            a_fmt = node.anchor(index).format
            for row, sect in self._ref_dict[node]:
                str_ops[sect].append(a_fmt)
        # Apply format strings for every section in the order they were added and join them.
        return "".join([_HEADER, *map(_apply, str_ops, self), _FOOTER])

    def node_at(self, index:str) -> Optional[GraphNode]:
        try:
            return self._ref_list[int(index)]
        except (IndexError, ValueError):
            return None


def _apply(fns, text):
    for fn in fns:
        text = fn(text)
    return text

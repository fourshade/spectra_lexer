from collections import defaultdict
from typing import Dict, List, Optional

from .node import BranchNode, GraphNode

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
        super().__init__([_HEADER])
        append = self.append
        ref_dict = self._ref_dict = defaultdict(list)
        row = 0
        for chars, refs in zip(lines, ref_grid):
            refs = [*refs, None]
            last_ref = refs[0]
            last_col = 0
            for col, ref in enumerate(refs):
                if ref is not last_ref:
                    if last_ref is not None:
                        ref_dict[last_ref].append((row, len(self)))
                    append(chars[last_col:col])
                    last_col, last_ref = col, ref
            append("\n")
            row += 1
        append(_FOOTER)
        self._ref_list = list(ref_dict)

    def _highlight(self, node:GraphNode, intense:bool) -> None:
        """ Highlight the full ancestry line of the selected node (starting with itself) up to the root. """
        start = 0
        length = node.attach_length
        args = ()
        while node is not None:
            # Highlight the entire original node and all fragments of ancestors directly above it.
            self._highlight_section(node, intense, *args)
            # Add the attach start offset for each node as we climb the ladder.
            start += node.attach_start
            args = (start, start + length)
            node = node.parent

    def _highlight_section(self, node:GraphNode, intense:bool, start:int=None, end:int=None) -> None:
        for row, sect in self._ref_dict[node][::-1]:
            r, g, b = node.color(row, intense)
            text = self[sect]
            if start is not None:
                pfx, text, sfx = text[:start], text[start:end], text[end:]
            self[sect] = f'<span style="color:#{r:02x}{g:02x}{b:02x};">{text}</span>'
            if start is not None:
                self[sect] = f'{pfx}{self[sect]}{sfx}'
                start = None

    def to_html(self, highlight_node:GraphNode=None, intense:bool=False) -> str:
        """ Render the graph inside preformatted tags with an optional node highlighted and bolded.
            Save the text before starting and restore it to its original state after. """
        saved = self[:]
        if highlight_node is not None:
            self._highlight(highlight_node, intense)
        # In addition to those highlighted, every node with children is bold by default (as is the root).
        for index, node in enumerate(self._ref_list):
            sections = self._ref_dict[node]
            if isinstance(node, BranchNode) or node is highlight_node:
                _, sect = sections[-1]
                self[sect] = f'<b>{self[sect]}</b>'
            for row, sect in sections:
                self[sect] = f'<a href="{index}">{self[sect]}</a>'
        text = "".join(self)
        self[:] = saved
        return text

    def node_at(self, index:str) -> Optional[GraphNode]:
        try:
            return self._ref_list[int(index)]
        except (IndexError, ValueError):
            return None

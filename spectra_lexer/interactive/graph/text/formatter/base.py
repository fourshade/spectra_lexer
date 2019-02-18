from collections import defaultdict
from typing import List


class TextFormatter(defaultdict):
    """ Holds and formats copies of a list of text lines each divided into sections based on node ownership.
        This list is indexed by section only. Each section is owned by a single node, and is formatted as a whole.
        Each row is terminated by an unowned newline section. Joining all sections produces the final text.
        The dict itself contains graph nodes each mapped to a list of (row, section) indices that node owns. """

    sections: List[str]  # Current working copy of sections to format.

    def __init__(self, lines:List[str], node_grid:List[list]):
        """ From a 2D node grid and corresponding list of character strings, find contiguous ranges of characters
            owned by a single node and create a section for each of them. Add each section of characters to the
            list, and record the row number and section index in the dict under the owner node. """
        super().__init__(list)
        self.sections = []
        sections_append = self.sections.append
        sect = 0
        for (row, (chars, node_row)) in enumerate(zip(lines, node_grid)):
            last_col = 0
            last_node = None
            for (col, node) in enumerate(node_row + [None]):
                if node is not last_node:
                    if last_node is not None:
                        self[last_node].append((row, sect))
                    sections_append(chars[last_col:col])
                    sect += 1
                    last_col, last_node = col, node
            sections_append("\n")
            sect += 1

    def format(self, section:int, fmt_string:str) -> None:
        """ Format a section of text with a format string. """
        s_list = self.sections
        s_list[section] = fmt_string.format(s_list[section])

    def format_part(self, section:int, col_start:int, col_end:int, fmt_string:str) -> None:
        """ Format only part of a section of text with a format string. """
        s_list = self.sections
        s = s_list[section]
        s_fmt = fmt_string.format(s[col_start:col_end])
        s_list[section] = s[:col_start] + s_fmt + s[col_end:]

    def text(self) -> str:
        """ Make the final text by joining the list of sections. """
        return "".join(self.sections)

from collections import defaultdict
from typing import List


class SectionedTextField:
    """ Holds and formats copies of a list of text lines each divided into sections based on ownership.
        The list is indexed by section only. Each section is owned by a single object, and is formatted as a whole.
        Each row is terminated by an unowned newline section. Joining all sections produces the final text. """

    _ref_dict: dict          # References each mapped to a list of (row, section) indices that ref owns.
    _sections: List[str]     # Reference field of text.
    _stack: List[List[str]]  # Stack of saved section lists.

    def __init__(self, lines:List[str], ref_grid:List[list]):
        """ From a 2D reference grid and corresponding list of character strings, find contiguous ranges of characters
            owned by a single reference and create a section for each of them. Add each section of characters to the
            list, and record the row number and section index in the dict under the owner reference. """
        ref_dict = self._ref_dict = defaultdict(list)
        sections = self._sections = []
        self._stack = []
        sect = 0
        for (row, (chars, refs)) in enumerate(zip(lines, ref_grid)):
            last_col = 0
            last_ref = None
            for (col, ref) in enumerate(refs + [None]):
                if ref is not last_ref:
                    if last_ref is not None:
                        ref_dict[last_ref].append((row, sect))
                    sections.append(chars[last_col:col])
                    sect += 1
                    last_col, last_ref = col, ref
            sections.append("\n")
            sect += 1

    def save(self) -> None:
        """ Save a copy of the sections to the next position on the stack. """
        self._stack.append(self._sections[:])

    def restore(self) -> None:
        """ Restore the sections to the previous position on the stack. """
        self._sections = self._stack.pop()

    def format(self, section:int, fmt_string:str, col_start:int=None, col_end:int=None) -> None:
        """ Format a section of text with a format string. """
        s = self._sections[section]
        # If <col_start> and <col_end> are not specified, format the whole section.
        if col_start is None and col_end is None:
            s_fmt = fmt_string.format(s)
        else:
            s_fmt = s[:col_start] + fmt_string.format(s[col_start:col_end]) + s[col_end:]
        self._sections[section] = s_fmt

    def to_string(self) -> str:
        """ Make a usable text string by joining the list of sections. """
        return "".join(self._sections)

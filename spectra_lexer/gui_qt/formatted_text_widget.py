from typing import Callable, Iterable, Tuple

from PyQt5.QtGui import QBrush, QColor, QFont, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QTextEdit

from spectra_lexer.display.cascaded_text import TextFormatInfo

# Cursor movement/selection constants for text formatting.
_TEXT_START = QTextCursor.Start
_TEXT_END = QTextCursor.End
_NEXT_ROW = QTextCursor.NextBlock
_ROW_START = QTextCursor.StartOfBlock
_RIGHT = QTextCursor.Right
_AND_SKIP = QTextCursor.MoveAnchor
_AND_SELECT = QTextCursor.KeepAnchor

# Merge this to reset_formatting formatting of text to the default.
_FORMAT_CLEAR = QTextCharFormat()
_FORMAT_CLEAR.setForeground(QBrush(QColor.fromRgb(0, 0, 0)))
_FORMAT_CLEAR.setFontWeight(QFont.Normal)
# Merge this to bold a range of text (may de-align box characters).
_FORMAT_BOLD = QTextCharFormat()
_FORMAT_BOLD.setFontWeight(QFont.Bold)


class FormattedTextWidget(QTextEdit):
    """ QTextEdit subclass that can format monospaced text from a (row, column) based info structure. """

    _current_row: int = 0               # Most recent row affected by operations.
    _move_to: Callable                  # Method for performing a move cursor operation.
    _format_selection: Callable         # Method for merging a char format with a text selection.

    def __init__(self, *args, **kwargs):
        """ We only need to save some of the formatting methods, not the cursor itself. """
        super().__init__(*args, **kwargs)
        cursor = self.textCursor()
        self._move_to = cursor.movePosition
        self._format_selection = cursor.mergeCharFormat

    def reset_formatting(self) -> None:
        """ Reset all special formatting on the text to default and move the cursor to start. """
        self._move_to(_TEXT_START)
        self._move_to(_TEXT_END, _AND_SELECT)
        self._format_selection(_FORMAT_CLEAR)
        self._move_to(_TEXT_START)
        self._current_row = 0

    def _move_to_row(self, row:int) -> None:
        """ Jump forward one row at a time from the last position to the new one.
            If we have to move backwards, just start from the beginning instead. """
        steps = row - self._current_row
        if steps < 0:
            self._move_to(_TEXT_START)
            steps = row
        for i in range(steps):
            self._move_to(_NEXT_ROW)
        self._current_row = row

    def _select_range(self, start:int, end:int) -> None:
        # Position the cursor at the start of the line, then move right until we arrive at range start.
        self._move_to(_ROW_START)
        self._move_to(_RIGHT, _AND_SKIP, start)
        # Move right by the range's length while holding the anchor to select the rule text.
        self._move_to(_RIGHT, _AND_SELECT, end - start)

    def _highlight_selection(self, rgb:Tuple[int, int, int], cache:dict={}) -> None:
        """ Change the color of the currently selected text to the given RGB 0-255 tuple. """
        color_fmt = cache.get(rgb)
        if color_fmt is None:
            cache[rgb] = color_fmt = QTextCharFormat()
            color_fmt.setForeground(QBrush(QColor.fromRgb(*rgb)))
        self._format_selection(color_fmt)

    def _bold_selection(self) -> None:
        """ Bold the currently selected text. """
        self._format_selection(_FORMAT_BOLD)

    def format_text(self, format_iter:Iterable[TextFormatInfo]) -> None:
        """ Add special formatting to the text based on a list of row format entries. """
        # Declare format methods as locals for both speed and clarity.
        move_to_row = self._move_to_row
        select_range = self._select_range
        highlight_selection = self._highlight_selection
        bold_selection = self._bold_selection
        # Clear formatting and perform a highlighting and/or bold operation on each row in the structure.
        self.reset_formatting()
        for row, start, end, color, bold in format_iter:
            move_to_row(row)
            select_range(start, end)
            highlight_selection(color)
            if bold:
                bold_selection()

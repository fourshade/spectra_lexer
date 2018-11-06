from typing import Callable, Iterable, Tuple

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QPoint
from PyQt5.QtGui import QBrush, QColor, QFont, QMouseEvent, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QTextEdit

from spectra_lexer.format.cascaded_text import CascadedTextDisplay, TextFormatInfo
from spectra_lexer.output import LexerOutput

# Cursor movement/selection constants for text formatting.
_TEXT_START = QTextCursor.Start
_TEXT_END = QTextCursor.End
_NEXT_ROW = QTextCursor.NextBlock
_ROW_START = QTextCursor.StartOfBlock
_RIGHT = QTextCursor.Right
_AND_SKIP = QTextCursor.MoveAnchor
_AND_SELECT = QTextCursor.KeepAnchor

# Merge this to reset formatting of text to the default.
_FORMAT_CLEAR = QTextCharFormat()
_FORMAT_CLEAR.setForeground(QBrush(QColor.fromRgb(0, 0, 0)))
_FORMAT_CLEAR.setFontWeight(QFont.Normal)
# Merge this to bold a range of text (may de-align box characters).
_FORMAT_BOLD = QTextCharFormat()
_FORMAT_BOLD.setFontWeight(QFont.Bold)

# Pixel offset to add when calculating character position from mouse cursor (half a column).
_CURSOR_X_OFFSET = 4


class _OutputTextFormatter:
    _current_row: int = 0               # Most recent row affected by operations.
    _move_to: Callable                  # Method for performing a move cursor operation.
    _format_selection: Callable         # Method for merging a char format with a text selection.

    def __init__(self, cursor):
        """ We only need to save some of the formatting methods, not the cursor itself. """
        self._move_to = cursor.movePosition
        self._format_selection = cursor.mergeCharFormat

    def reset(self) -> None:
        """ Reset all special formatting on the text to default and move the cursor to start. """
        self._move_to(_TEXT_START)
        self._move_to(_TEXT_END, _AND_SELECT)
        self._format_selection(_FORMAT_CLEAR)
        self._move_to(_TEXT_START)
        self._current_row = 0

    def move_to_row(self, row:int) -> None:
        """ Jump forward one row at a time from the last position to the new one.
            If we have to move backwards, just start from the beginning instead. """
        steps = row - self._current_row
        if steps < 0:
            self._move_to(_TEXT_START)
            steps = row
        for i in range(steps):
            self._move_to(_NEXT_ROW)
        self._current_row = row

    def select_range(self, start:int, end:int) -> None:
        # Position the cursor at the start of the line, then move right until we arrive at range start.
        self._move_to(_ROW_START)
        self._move_to(_RIGHT, _AND_SKIP, start)
        # Move right by the range's length while holding the anchor to select the rule text.
        self._move_to(_RIGHT, _AND_SELECT, end - start)

    def highlight_selection(self, rgb:Tuple[int,int,int], cache:dict={}) -> None:
        """ Change the color of the currently selected text to the given RGB 0-255 tuple. """
        color_fmt = cache.get(rgb)
        if color_fmt is None:
            cache[rgb] = color_fmt = QTextCharFormat()
            color_fmt.setForeground(QBrush(QColor.fromRgb(*rgb)))
        self._format_selection(color_fmt)

    def bold_selection(self) -> None:
        """ Bold the currently selected text. """
        self._format_selection(_FORMAT_BOLD)


class OutputTextWidget(QTextEdit):
    """ Text widget whose sole purpose is to display and respond to interaction with a
        monospaced text grid representation of the breakdown of English text by steno rules. """

    _last_output: CascadedTextDisplay = None   # Most recent lexer output (if any).
    _last_info: object = None                  # Most recent info object from a mouse move event (only ref matters).
    _formatter: _OutputTextFormatter

    def __init__(self, *args, **kwargs):
        """ Set up mouse tracking to capture mouse move events and create formatting objects. """
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self._formatter = _OutputTextFormatter(self.textCursor())

    def set_output(self, out:LexerOutput) -> None:
        """ Generate and display the text from the format object. Save it for later reference. """
        text_output = CascadedTextDisplay(out.make_tree())
        self._formatter.reset()
        self.setText(text_output.text)
        self._last_output = text_output

    # Signals
    ruleSelected = pyqtSignal([str, str])

    # Slots
    @pyqtSlot(QMouseEvent)
    def mouseMoveEvent(self, event:QMouseEvent) -> None:
        """ If the mouse has moved over a rule, try to find out what it is and display information. """
        # Don't bother if there's no results for some reason or another.
        if self._last_output:
            # The mouse's position relative to the top-left corner of the text display is what we're interested in.
            # Take the position of the text display, minus an empirically determined offset
            # to compensate for the fact that the cursor stays between characters.
            local_pos = event.pos()
            local_pos -= QPoint(_CURSOR_X_OFFSET, 0)
            location_cursor = self.cursorForPosition(local_pos)
            # Get the row and column of the mouse's position within the text and see if there's
            # a rule displayed within that range. We will get a rule info object back if there is.
            row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
            info = self._last_output.get_info_at(col, row)
            # It's only worth updating the display if it's not the same info we just saw (and isn't None).
            if info is not None and info is not self._last_info:
                # Set the new formatting from the rule info.
                self._format_info(info.format_info)
                # Send a signal with the rule's keys and description.
                self.ruleSelected.emit(info.keys, info.description)
                # Store the current info so we can avoid redraw.
                self._last_info = info

    def _format_info(self, format_iter:Iterable[TextFormatInfo]) -> None:
        """ Add special formatting to the text based on a list of row format entries. """
        # Declare format methods as locals for both speed and clarity.
        move_to_row = self._formatter.move_to_row
        select_range = self._formatter.select_range
        highlight_selection = self._formatter.highlight_selection
        bold_selection = self._formatter.bold_selection
        # Clear formatting and perform a highlighting and/or bold operation on each row in the structure.
        self._formatter.reset()
        for row, start, end, color, bold in format_iter:
            move_to_row(row)
            select_range(start, end)
            highlight_selection(color)
            if bold:
                bold_selection()

from typing import Iterable, Tuple

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QPoint
from PyQt5.QtGui import QBrush, QColor, QFont, QMouseEvent, QTextCharFormat, QTextCursor
from PyQt5.QtWidgets import QTextEdit

from spectra_lexer.format.cascaded_text import CascadedTextDisplay, TextRuleInfo
from spectra_lexer.output import LexerOutput

HIGHLIGHT_COLOR_RGB = (32, 32, 255)             # Color of the text when highlighted in RGB 0-255 format.
CURSOR_X_OFFSET = 4                             # Pixel offset to add when calculating cursor position (half a column).
ASCII_CHARS = set(map(chr, range(0x21, 0x7F)))  # Set containing all printable ASCII characters.

class OutputTextWidget(QTextEdit):
    """ Text widget whose sole purpose is to display and respond to interaction with a
        monospaced text grid representation of the breakdown of English text by steno rules. """

    _last_output: CascadedTextDisplay = None   # Most recent lexer output (if any).
    _last_info: TextRuleInfo = None            # Most recent info object from a mouse move event.
    _format_clear: QTextCharFormat             # Merge this to reset formatting of text to the default.
    _format_highlight: QTextCharFormat         # Merge this to highlight a range of text with a foreground color.
    _format_bold: QTextCharFormat              # Merge this to bold a range of text (may de-align box characters).

    def __init__(self, *args, **kwargs):
        """ Set up mouse tracking to capture mouse move events and create formatting objects """
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self._format_clear = QTextCharFormat()
        self._format_clear.setForeground(QBrush(QColor.fromRgb(0, 0, 0)))
        self._format_clear.setFontWeight(QFont.Normal)
        self._format_highlight = QTextCharFormat()
        self._format_highlight.setForeground(QBrush(QColor.fromRgb(*HIGHLIGHT_COLOR_RGB)))
        self._format_bold = QTextCharFormat()
        self._format_bold.setFontWeight(QFont.Bold)

    def set_output(self, out:LexerOutput) -> None:
        """ Generate and display the text from the format object. Save it for later reference. """
        text_output = CascadedTextDisplay(out.make_tree())
        self.setCurrentCharFormat(self._format_clear)
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
            local_pos -= QPoint(CURSOR_X_OFFSET, 0)
            cursor = self.cursorForPosition(local_pos)
            # Get the row and column of the mouse's position within the text and see if there's
            # a rule displayed within that range. We will get a rule info object back if there is.
            row, col = cursor.blockNumber(), cursor.columnNumber()
            info = self._last_output.get_info_at(col, row)
            # It's only worth updating the display if it's not the same info we just saw (and isn't None).
            if info and info is not self._last_info:
                # Clear all formatting from the previous rule (if any).
                self._clear_formatting(cursor)
                # Add the new formatting from the rule info.
                self._add_formatting(cursor, info.highlight_ranges.items())
                # Send a signal with the rule's keys and description.
                self.ruleSelected.emit(info.keys, info.description)
                # Store the current info so we can avoid redraw.
                self._last_info = info

    def _clear_formatting(self, cursor:QTextCursor) -> None:
        """ Reset all special formatting on the text to default. """
        cursor.movePosition(QTextCursor.Start)
        cursor.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        cursor.mergeCharFormat(self._format_clear)

    def _add_formatting(self, cursor:QTextCursor, row_iter:Iterable[Tuple[int, range]]) -> None:
        """ Add special formatting to the text based on a dict of [row: range(startcol,endcol)] entries. """
        # Declare cursor constants as locals for both speed and clarity.
        move_cursor = cursor.movePosition
        set_format = cursor.mergeCharFormat
        _to_start = QTextCursor.Start
        _to_next_row = QTextCursor.NextBlock
        _to_row_start = QTextCursor.StartOfBlock
        _right = QTextCursor.Right
        _and_skip = QTextCursor.MoveAnchor
        _and_select = QTextCursor.KeepAnchor
        # Perform a highlighting operation on each row in the structure.
        move_cursor(_to_start)
        last_row = 0
        for row, rng in row_iter:
            # Jump forward from the last position until the next row is reached (the dict rows must be in order).
            steps = row - last_row
            for i in range(steps):
                move_cursor(_to_next_row)
            # Position the cursor at the start of the line, then move right until we arrive at range start.
            move_cursor(_to_row_start)
            move_cursor(_right, _and_skip, rng[0])
            # Move right by the range's length while holding the anchor to select the rule text.
            move_cursor(_right, _and_select, len(rng))
            # Highlight the text range and mark this as the last highlighted row.
            # If ASCII text is involved (not just box-drawing characters), bold it as well.
            set_format(self._format_highlight)
            if any(c in ASCII_CHARS for c in cursor.selectedText()):
                set_format(self._format_bold)
            last_row = row

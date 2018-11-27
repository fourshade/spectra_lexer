from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTextEdit

# Pixel offset to add when calculating character position from mouse cursor (half a column).
_CURSOR_X_OFFSET = 1

class TextGraphWidget(QTextEdit):
    """ Formatted text widget whose sole purpose is to display and respond to interaction
        with a monospaced text graph of the breakdown of English text by steno rules. """

    _last_row: int = -1  # Row number of last detected character under mouse cursor
    _last_col: int = -1  # Column number of last detected character under mouse cursor

    def set_graph(self, text:str, reset_scrollbar:bool=True) -> None:
        """ Set the text content of the graph and optionally scroll back to the top (if it exceeded the borders). """
        # Scroll position is automatically reset when the text is set in this widget.
        # The scroll position values must be saved and restored if we want to *stop* them from resetting.
        sx = self.horizontalScrollBar().value()
        sy = self.verticalScrollBar().value()
        self.setHtml(text)
        if not reset_scrollbar:
            self.horizontalScrollBar().setValue(sx)
            self.verticalScrollBar().setValue(sy)

    # Signals
    mouseOverCharacter = pyqtSignal([int, int])

    # Slots
    def mouseMoveEvent(self, event:QMouseEvent) -> None:
        """ If the mouse has moved over the text, try to find out where it is to display information. """
        # The mouse's position relative to the top-left corner of the text display is what we're interested in.
        # Take the position of the text display, minus an empirically determined offset based on the GUI layout.
        local_pos = event.pos()
        local_pos -= QPoint(_CURSOR_X_OFFSET, 0)
        location_cursor = self.cursorForPosition(local_pos)
        # Get the row and column of the mouse's position within the text and see if there's
        # a rule displayed within that range. Don't waste time if the row and column are the same as before.
        row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
        if self._last_row != row or self._last_col != col:
            self.mouseOverCharacter.emit(row, col)
            self._last_row = row
            self._last_col = col

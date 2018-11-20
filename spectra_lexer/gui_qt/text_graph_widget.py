from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QMouseEvent

from spectra_lexer.gui_qt.formatted_text_widget import FormattedTextWidget

# Pixel offset to add when calculating character position from mouse cursor (half a column).
_CURSOR_X_OFFSET = 4

class TextGraphWidget(FormattedTextWidget):
    """ Formatted text widget whose sole purpose is to display and respond to interaction
        with a monospaced text graph of the breakdown of English text by steno rules. """

    _last_row: int = -1  # Row number of last detected character under mouse cursor
    _last_col: int = -1  # Column number of last detected character under mouse cursor

    def __init__(self, *args, **kwargs):
        """ Set up mouse tracking to capture mouse move events and create formatting objects. """
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

    def set_output(self, text_output:str) -> None:
        """ Display the text from the output object. """
        self.setText(text_output)

    # Signals
    mouseover_text_graph = pyqtSignal([int, int])

    # Slots
    def mouseMoveEvent(self, event:QMouseEvent) -> None:
        """ If the mouse has moved over the text, try to find out where it is to display information. """
        # The mouse's position relative to the top-left corner of the text display is what we're interested in.
        # Take the position of the text display, minus an empirically determined offset
        # to compensate for the fact that the cursor stays between characters.
        local_pos = event.pos()
        local_pos -= QPoint(_CURSOR_X_OFFSET, 0)
        location_cursor = self.cursorForPosition(local_pos)
        # Get the row and column of the mouse's position within the text and see if there's
        # a rule displayed within that range. Don't waste time if the row and column are the same as before.
        row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
        if self._last_row != row or self._last_col != col:
            self.mouseover_text_graph.emit(row, col)
            self._last_row = row
            self._last_col = col

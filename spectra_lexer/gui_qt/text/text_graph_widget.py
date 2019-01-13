from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTextEdit

# Pixel offset to add when calculating character position from mouse cursor.
_CURSOR_X_OFFSET = 1


class TextGraphWidget(QTextEdit):
    """ Formatted text widget meant to display a monospaced HTML text graph of the breakdown
        of English text by steno rules as well as basic plaintext interpreter output. """

    _last_row: int = -1        # Row number of last detected character under mouse cursor
    _last_col: int = -1        # Column number of last detected character under mouse cursor
    _interactive: bool = True  # Does moving the mouse over the text do anything?

    def set_text_display(self, text:str, *, html:bool=False, interactive:bool=True, scroll_to:str="top") -> None:
        """ Set the text content of the widget and <scroll_to> the top or bottom (or don't if scroll_to=None). """
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        # HTML content requires special parsing. Make sure normal text has it disabled.
        if html:
            self.setHtml(text)
        else:
            self.setPlainText(text)
        # Scroll position is automatically reset to the top when the text is set in this widget.
        if scroll_to is None:
            # The scroll values must be manually restored to negate any scrolling effect.
            sx.setValue(px)
            sy.setValue(py)
        elif scroll_to == "bottom":
            # To keep up with scrolling text, the vertical scroll position can be fixed at the bottom as well.
            sy.setValue(sy.maximum())
        # If specified, turn interactivity (mouseover response) on or off.
        self._interactive = interactive

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
        # Get the row and column of the mouse's position within the text and see if there's a rule
        # displayed within that range. Don't waste time if the row and column are the same as before.
        row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
        if self._interactive and (self._last_row != row or self._last_col != col):
            self.mouseOverCharacter.emit(row, col)
            self._last_row = row
            self._last_col = col

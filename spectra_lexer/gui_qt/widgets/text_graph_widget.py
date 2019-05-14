from typing import Callable

from PyQt5.QtCore import pyqtSignal, QPoint
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtWidgets import QTextEdit

# Pixel offset to add when calculating character position from mouse cursor.
_CURSOR_OFFSET = QPoint(-1, 0)
# Pixel offset to add when the character position is ambiguous.
_TEST_SHIFT = QPoint(0, 1)


class MouseEventSignaller:

    _last_row: int = -1                        # Row number of last detected character under mouse cursor.
    _last_col: int = -1                        # Column number of last detected character under mouse cursor.
    _signal: Callable[[int, int, bool], None]  # Call to send a mouse event (row, col, clicked) to the engine.

    def __init__(self, signal:Callable):
        self._signal = signal

    def check_event(self, row:int, col:int, clicked:bool=False) -> None:
        """ Check to see if any events need to be sent.
            Don't waste time if there's no click and the row and column haven't changed. """
        if clicked or (self._last_row != row or self._last_col != col):
            self._last_row = row
            self._last_col = col
            self._signal(row, col, clicked)


class TextGraphWidget(QTextEdit):
    """ Formatted text widget meant to display a monospaced HTML text graph of the breakdown of English text
        by steno rules as well as plaintext interpreter output such as error messages and exceptions. """

    _signaller: MouseEventSignaller  # Sends mouse events for character position changes.
    _mouse_enabled: bool = True      # Does moving the mouse over the text do anything?

    def __init__(self, *args):
        super().__init__(*args)
        self._signaller = MouseEventSignaller(self.textMouseAction.emit)

    def set_plaintext(self, text:str) -> None:
        """ Add plaintext to the widget. If it was in interactive mode before, completely replace the text instead. """
        if self._mouse_enabled:
            self._mouse_enabled = False
        else:
            text = f"{self.toPlainText()}\n\n{text}"
        self.setPlainText(text)

    def set_interactive_text(self, text:str, *, scroll_to:str="top") -> None:
        """ Enable the mouse and replace the current text with new HTML formatted text.
            Optionally <scroll_to> the "top" or "bottom" (or don't if scroll_to=None). """
        self._mouse_enabled = True
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self.setHtml(text)
        # Scroll position is automatically reset to the top when the text is set in this widget.
        if scroll_to is None:
            # The scroll values must be manually restored to negate any scrolling effect.
            sx.setValue(px)
            sy.setValue(py)
        elif scroll_to == "bottom":
            # To keep up with scrolling text, the vertical scroll position can be fixed at the bottom as well.
            sy.setValue(sy.maximum())

    def mouseMoveEvent(self, event:QMouseEvent) -> None:
        """ If the mouse has moved over the text, try to find out where it is to display information. """
        if not self._try_mouse(event, clicked=False):
            super().mouseMoveEvent(event)

    def mousePressEvent(self, event:QMouseEvent) -> None:
        """ A mouse click always sends an event for the current character position (if enabled).
            If not enabled, pass the event up so that manual text selection and copy is possible. """
        if not self._try_mouse(event, clicked=True):
            super().mousePressEvent(event)

    def _try_mouse(self, event:QMouseEvent, clicked:bool) -> bool:
        """ If the mouse is enabled, get its position and find the character it's pointing at. """
        if not self._mouse_enabled:
            return False
        # The mouse's position relative to the top-left corner of the text display is what we're interested in.
        # Take the position of the text display, plus an empirically determined offset based on the GUI layout.
        local_pos = event.pos() + _CURSOR_OFFSET
        location_cursor = self.cursorForPosition(local_pos)
        if location_cursor.atBlockEnd():
            # If the cursor is between rows, it may erroneously read as being at the end of the text.
            # Add a tiny amount and test again. If it really is at the end of the text, it won't matter.
            location_cursor = self.cursorForPosition(local_pos + _TEST_SHIFT)
        row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
        self._signaller.check_event(row, col, clicked)
        return True

    # Signals
    textMouseAction = pyqtSignal([int, int, bool])

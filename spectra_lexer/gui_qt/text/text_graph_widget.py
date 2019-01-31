from PyQt5.QtCore import pyqtSignal, QPoint, Qt
from PyQt5.QtGui import QKeyEvent, QMouseEvent, QTextCursor
from PyQt5.QtWidgets import QTextEdit

# Pixel offset to add when calculating character position from mouse cursor.
_CURSOR_X_OFFSET = 1


class TextGraphWidget(QTextEdit):
    """ Formatted text widget meant to display a monospaced HTML text graph of the breakdown of English text
        by steno rules as well as plaintext interpreter input and output, error messages, exceptions, etc. """

    _last_row: int = -1             # Row number of last detected character under mouse cursor
    _last_col: int = -1             # Column number of last detected character under mouse cursor
    _last_text_received: str = ""   # Last text received from outside, used as an unchangeable base for text input.
    _last_text_good: str = ""       # Last text known to be a result of valid keyboard input.
    _keyboard_enabled: bool = True  # Can keyboard input change the text (specifically, add to the end)?
    _mouse_enabled: bool = True     # Does moving the mouse over the text do anything?

    def set_interactive_text(self, text:str, *, keyboard:bool=False, mouse:bool=False, **kwargs) -> None:
        """ Set the text content of the widget (without triggering signals) and set interactivity on/off. """
        self.set_text(text, **kwargs)
        # Turn keyboard and/or mouse interactivity on or off by enabling/disabling event handlers and flags.
        # Only mess with the flags if it's a change from the previous mode.
        if self._keyboard_enabled != keyboard or self._mouse_enabled != mouse:
            self._keyboard_enabled = keyboard
            self._mouse_enabled = mouse
            flags = Qt.TextSelectableByMouse
            if keyboard:
                flags |= Qt.TextEditorInteraction
                self._reset_cursor()
            self.setTextInteractionFlags(flags)

    def set_text(self, text:str, *, html:bool=False, scroll_to:str="top") -> None:
        """ Set the text content of the widget and <scroll_to> the top or bottom (or don't if scroll_to=None). """
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self._set_content(text, html)
        # Scroll position is automatically reset to the top when the text is set in this widget.
        if scroll_to is None:
            # The scroll values must be manually restored to negate any scrolling effect.
            sx.setValue(px)
            sy.setValue(py)
        elif scroll_to == "bottom":
            # To keep up with scrolling text, the vertical scroll position can be fixed at the bottom as well.
            sy.setValue(sy.maximum())

    def _set_content(self, text:str, html:bool=False):
        """ Set text and cursor while suppressing text change signals. """
        self.blockSignals(True)
        # HTML content requires special parsing. Make sure normal text is only interpreted as plaintext.
        if html:
            self.setHtml(text)
        else:
            self.setPlainText(text)
        self.blockSignals(False)
        self._last_text_received = self._last_text_good = text

    def _reset_cursor(self):
        """ Only reset the cursor to the end if it matters (keyboard input mode started). """
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        self.setTextCursor(c)

    # Signals
    mouseInteraction = pyqtSignal([int, int, bool])
    textInputComplete = pyqtSignal([str])

    # Slots
    def mouseMoveEvent(self, event:QMouseEvent) -> None:
        """ If the mouse has moved over the text, try to find out where it is to display information. """
        if not self._mouse_enabled:
            return
        # The mouse's position relative to the top-left corner of the text display is what we're interested in.
        # Take the position of the text display, minus an empirically determined offset based on the GUI layout.
        local_pos = event.pos()
        local_pos -= QPoint(_CURSOR_X_OFFSET, 0)
        location_cursor = self.cursorForPosition(local_pos)
        # Get the row and column of the mouse's position within the text and see if there's a rule
        # that owns that character. Don't waste time if the row and column are the same as before.
        row, col = location_cursor.blockNumber(), location_cursor.columnNumber()
        if self._last_row != row or self._last_col != col:
            # Switch the arguments to put it in (x, y) order.
            self.mouseInteraction.emit(col, row, False)
            self._last_row = row
            self._last_col = col

    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ If the text changed as the result of user input, make sure it didn't erase anything we started with. """
        super().keyPressEvent(event)
        if not self._keyboard_enabled:
            return
        text = self.toPlainText()
        original = self._last_text_received
        if not text.startswith(original):
            # Reset text to be what it was at the last output command while suppressing text change signals.
            self._set_content(original)
            self._reset_cursor()
            return
        # This text is good, so keep it. If a newline is entered, send only the user-provided text in a signal.
        self._last_text_good = text
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and text.endswith("\n"):
            self._set_content(original)
            user_str = text[len(original):-1]
            if user_str:
                self.textInputComplete.emit(user_str)
            self._reset_cursor()

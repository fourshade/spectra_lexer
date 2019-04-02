from typing import Callable

from PyQt5.QtCore import pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout

from spectra_lexer.gui_qt.tools.dialog import ToolDialog
from spectra_lexer.utils import delegate_to


class HistoryTracker(list):
    """ Tracks previous lines of keyboard input, minus the newline. """

    _pointer: int = 0  # Pointer to current history line, 0 = earliest line.

    def add(self, s:str) -> None:
        """ Add a new line to the history and reset the pointer to just after the end. """
        self.append(s)
        self._pointer = len(self)

    def prev(self) -> str:
        """ Scroll the history backward and return the next line. """
        self._pointer -= 1
        return self.get()

    def next(self) -> str:
        """ Scroll the history forward and return the next line. """
        self._pointer += 1
        return self.get()

    def get(self) -> str:
        """ Return the line at the pointer after bounds checking. """
        self._pointer = min(max(self._pointer, 0), len(self) - 1)
        return self[self._pointer] if self else ""


class ConsoleTextWidget(QTextEdit):
    """ Formatted text widget meant to display plaintext interpreter input and output. """

    _history: HistoryTracker        # Tracks previous keyboard input.
    _last_text_received: str = ""   # Last text received from outside, used as an unchangeable base for text input.

    def __init__(self, parent:ToolDialog, input_cb:Callable):
        """ Create the widget and connect the callback for a new line of input. """
        super().__init__(parent)
        self.setFont(QFont("Courier New", 10))
        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextEditorInteraction)
        self.textKeyboardInput.connect(input_cb)
        self._history = HistoryTracker()

    def add_text(self, text:str) -> None:
        """ Add to the text content of the widget and reset the cursor to the end. """
        self._last_text_received += text
        self._set_content(self._last_text_received)
        # To keep up with scrolling text, the vertical scroll position is fixed at the bottom.
        sy = self.horizontalScrollBar()
        sy.setValue(sy.maximum())

    def _set_content(self, text:str) -> None:
        """ Set new text content and reset the cursor to the end. """
        self.setPlainText(text)
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        self.setTextCursor(c)

    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Check the input for special cases. Make sure the cursor can't erase anything we started with. """
        self._set_cursor_valid()
        original = self._last_text_received
        # Up/down arrow keys will scroll through the command history.
        if event.key() == Qt.Key_Up:
            self._set_content(original + self._history.prev())
        elif event.key() == Qt.Key_Down:
            self._set_content(original + self._history.next())
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # If a newline is entered, send only the user-provided text in a signal.
            user_str = self.toPlainText()[len(original):]
            self._history.add(user_str)
            self.textKeyboardInput.emit(user_str)
        else:
            # In any other case, pass the keypress as normal and re-validate the cursor.
            super().keyPressEvent(event)
            self._set_cursor_valid()

    def insertFromMimeData(self, data:QMimeData):
        """ On a paste attempt, reset the cursor if necessary and paste only the plaintext content. """
        if data.hasText():
            self._set_cursor_valid()
            plaintext = QMimeData()
            plaintext.setText(data.text())
            super().insertFromMimeData(plaintext)

    def _set_cursor_valid(self):
        """ If the cursor is not within the current prompt, move it there. """
        min_position = len(self._last_text_received)
        c = self.textCursor()
        if c.position() < min_position:
            c.setPosition(min_position)
            self.setTextCursor(c)

    # Signals
    textKeyboardInput = pyqtSignal([str])


class ConsoleDialog(ToolDialog):
    """ Qt console dialog window object. Routes signals between the console, a text widget, and the keyboard. """

    TITLE = "Python Console"
    SIZE = (600, 400)

    w_text: ConsoleTextWidget = None  # The only window content; a giant console text box.

    def make_layout(self, input_cb:Callable) -> None:
        """ Create and add the sole widget to a vertical layout. """
        layout = QVBoxLayout(self)
        self.w_text = ConsoleTextWidget(self, input_cb)
        layout.addWidget(self.w_text)

    add_text = delegate_to("w_text")

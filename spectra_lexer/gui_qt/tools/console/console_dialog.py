from typing import Callable

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout

from spectra_lexer.gui_qt.tools.dialog import ToolDialog
from spectra_lexer.utils import delegate_to


class HistoryTracker(list):
    """ Tracks previous lines of keyboard input, minus the newline. """

    _pointer: int = 0  # Pointer to current history line, 0 = earliest line.

    def next(self, dir_back:bool=True) -> str:
        """ Scroll the history backward or forward (within bounds) and return the next line. """
        if not self:
            return ""
        self._pointer += -1 if dir_back else 1
        self._pointer = min(max(self._pointer, 0), len(self) - 1)
        return self[self._pointer]

    def add(self, s:str) -> None:
        """ Add a new line to the history and reset the pointer to just after the end. """
        self.append(s.strip())
        self._pointer = len(self)


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

    def set_text(self, text:str) -> None:
        """ Set the text content of the widget and reset the cursor to the end. """
        self._set_content(text)
        self._last_text_received = text
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
        """ If the text changed as the result of user input, make sure it didn't erase anything we started with. """
        super().keyPressEvent(event)
        text = self.toPlainText()
        original = self._last_text_received
        if not text.startswith(original):
            self._set_content(original)
        elif event.key() in (Qt.Key_Up, Qt.Key_Down):
            # The arrow keys will scroll through the command history.
            self._set_content(original + self._history.next(event.key() == Qt.Key_Up))
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter) and text.endswith("\n"):
            # If a newline is entered, send only the user-provided text in a signal.
            user_str = text[len(original):]
            self._history.add(user_str)
            self.textKeyboardInput.emit(user_str)

    # Signals
    textKeyboardInput = pyqtSignal([str])


class ConsoleDialog(ToolDialog):
    """ Qt console dialog window object. Routes signals between the console, a text widget, and the keyboard. """

    TITLE = "Python Console"
    SIZE = (600, 400)

    w_text: ConsoleTextWidget = None  # The only window content; a giant console text box.

    def make_layout(self) -> None:
        """ Create and add the sole widget to a vertical layout. """
        layout = QVBoxLayout(self)
        self.w_text = ConsoleTextWidget(self, self.submit_cb)
        layout.addWidget(self.w_text)

    set_text = delegate_to("w_text")

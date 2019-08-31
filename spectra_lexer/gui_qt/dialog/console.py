from PyQt5.QtCore import pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt5.QtWidgets import QTextEdit, QVBoxLayout

from .dialog import ToolDialog
from spectra_lexer.console import SystemConsole


class HistoryTracker:
    """ Tracks previous lines of keyboard input, minus the newline. """

    def __init__(self) -> None:
        """ There will always be at least one empty line, at the beginning. """
        self._lines = [""]  # Tracked sections of text. May include internal newline characters.
        self._pointer = 0   # Pointer to current history line, 0 = earliest line.

    def add(self, s:str) -> None:
        """ Add a new line to the history and reset the pointer to just *after* the end.
            This means the next access will read this line no matter which way we move. """
        self._lines.append(s)
        self._pointer = len(self._lines)

    def prev(self) -> str:
        """ Scroll the history backward and return the next line. """
        return self.get(-1)

    def next(self) -> str:
        """ Scroll the history forward and return the next line. """
        return self.get(1)

    def get(self, increment:int=0) -> str:
        """ Return the line at the pointer after moving it and checking the bounds. """
        self._pointer = min(max(self._pointer + increment, 0), len(self._lines) - 1)
        return self._lines[self._pointer]


class ConsoleTextWidget(QTextEdit):
    """ Formatted text widget meant to display plaintext interpreter input and output as a terminal. """

    textKeyboardInput = pyqtSignal([str])  # Sent with a line of user input upon pressing Enter.

    def __init__(self, parent:ToolDialog) -> None:
        super().__init__(parent)
        self._history = HistoryTracker()  # Tracks previous keyboard input.
        self._last_text_received = ""     # Last external text received; used as an unchangeable base for text input.

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
            # If a newline is entered, capture only the user-provided text.
            # Add it to the history, append it to the saved text (with newline), and send it in a signal.
            user_str = self.toPlainText()[len(original):]
            self._history.add(user_str)
            self.add_text(user_str + "\n")
            self.textKeyboardInput.emit(user_str)
        else:
            # In any other case, pass the keypress as normal. Undo anything that modifies the previous text.
            super().keyPressEvent(event)
            if not self.toPlainText().startswith(original):
                self.undo()
            self._set_cursor_valid()

    def insertFromMimeData(self, data:QMimeData) -> None:
        """ On a paste attempt, reset the cursor if necessary and paste only the plaintext content. """
        if data.hasText():
            self._set_cursor_valid()
            plaintext = QMimeData()
            plaintext.setText(data.text())
            super().insertFromMimeData(plaintext)

    def _set_cursor_valid(self) -> None:
        """ If the cursor is not within the current prompt, move it there. """
        min_position = len(self._last_text_received)
        c = self.textCursor()
        if c.position() < min_position:
            c.setPosition(min_position)
            self.setTextCursor(c)


class ConsoleDialog(ToolDialog):
    """ Qt console dialog window object. Routes signals between the console, a text widget, and the keyboard. """

    def setup(self, locals_ns:dict) -> None:
        """ Create a console widget and connect it to a new interpreter console instance. """
        self.setup_window("Python Console", 680, 480)
        w_text = ConsoleTextWidget(self)
        w_text.setFont(QFont("Courier New", 10))
        w_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextEditorInteraction)
        console = SystemConsole(locals_ns, write_to=w_text.add_text)
        w_text.textKeyboardInput.connect(console)
        layout = QVBoxLayout(self)
        layout.addWidget(w_text)

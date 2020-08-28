from typing import Any, Callable

from PyQt5.QtCore import pyqtSignal, QMimeData, Qt
from PyQt5.QtGui import QFont, QKeyEvent, QTextCursor
from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout

# Callbacks for terminal input and keyboard interrupts. Return values are ignored.
InputCallback = Callable[[str], Any]
InterruptCallback = Callable[[], Any]


class HistoryTracker:
    """ Tracks previous lines of keyboard input, minus the newline. """

    def __init__(self) -> None:
        """ There will always be at least one empty line, at the beginning. """
        self._lines = [""]  # Tracked sections of text. May include internal newline characters.
        self._pointer = 0   # Pointer to current history line, 0 = earliest line.

    def _move(self, offset:int) -> str:
        """ Return the line at the pointer after moving it and checking the bounds. """
        self._pointer = min(max(self._pointer + offset, 0), len(self._lines) - 1)
        return self._lines[self._pointer]

    def add(self, s:str) -> None:
        """ Add a new line to the history and reset the pointer to just *after* the end.
            This means the next access will read this line no matter which way we move. """
        self._lines.append(s)
        self._pointer = len(self._lines)

    def prev(self) -> str:
        """ Scroll the history backward and return the next line. """
        return self._move(-1)

    def next(self) -> str:
        """ Scroll the history forward and return the next line. """
        return self._move(1)


class TerminalTextWidget(QTextEdit):
    """ Formatted text widget meant to display plaintext interpreter input and output as a line-buffered terminal.
        The text content is composed of two parts. The "base text" includes everything before the prompt.
        This is the terminal's saved output; it may be copied but not be edited.
        The "user text" comes after the prompt; it is freely modifiable by the user.
        When the user presses Enter, the user text is sent in a signal, then frozen into the base text. """

    lineEntered = pyqtSignal([str])  # Sent with a line of user input on pressing Enter.
    interrupted = pyqtSignal([])     # Sent when a Ctrl-C interrupt occurs.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._base_text = ""              # Unchangeable base text. User input may only appear after this.
        self._user_text = ""              # Last valid state of user input text.
        self._history = HistoryTracker()  # Tracks previous keyboard input.
        self.setFont(QFont("Courier New", 10))
        self.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextEditorInteraction)
        self.textChanged.connect(self._on_edited)

    def _set_cursor_valid(self) -> None:
        """ If the cursor is not within the current prompt, move it to the end. """
        c = self.textCursor()
        prompt_start = len(self._base_text)
        if c.position() < prompt_start:
            c.movePosition(QTextCursor.End)
            self.setTextCursor(c)

    def _update(self) -> None:
        """ Update the widget's text content and reset the cursor without triggering signals. """
        self.blockSignals(True)
        self.setPlainText(self._base_text + self._user_text)
        self._set_cursor_valid()
        self.blockSignals(False)

    def _on_edited(self) -> None:
        """ Undo anything that modifies the base text. """
        current_text = self.toPlainText()
        start = len(self._base_text)
        if current_text[:start] == self._base_text:
            self._user_text = current_text[start:]
        else:
            self._update()

    def _submit(self) -> None:
        """ Add the current user text to the history, freeze it as an echo with a newline, and emit it as a signal. """
        text = self._user_text
        self._history.add(text)
        line = text + "\n"
        self._base_text += line
        self._user_text = ""
        self._update()
        self.lineEntered.emit(line)

    def _history_prev(self) -> None:
        """ Overwrite the user text with the previous item in the history. """
        self._user_text = self._history.prev()
        self._update()

    def _history_next(self) -> None:
        """ Overwrite the user text with the next item in the history. """
        self._user_text = self._history.next()
        self._update()

    def write(self, text:str) -> None:
        """ Add to the base text without disturbing the user text.
            To keep up with scrolling text, the vertical scroll position shifts to the bottom. """
        self._base_text += text
        self._update()
        sy = self.horizontalScrollBar()
        sy.setValue(sy.maximum())

    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Parse keyboard input events for special cases. """
        key = event.key()
        if key == Qt.Key_Up:
            # Up - replace user text with the previous command history item.
            self._history_prev()
        elif key == Qt.Key_Down:
            # Down - replace user text with the next command history item.
            self._history_next()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            # Enter - submit user text as terminal input.
            self._submit()
        elif event.modifiers() & Qt.ControlModifier:
            # Ctrl shortcuts have spurious event text.
            if key == Qt.Key_C and not self.textCursor().selectedText():
                # Ctrl-C is an interrupt if no text is selected; otherwise it is a copy.
                self.interrupted.emit()
            else:
                super().keyPressEvent(event)
        else:
            # In all other cases, process the event as normal.
            if event.text():
                # Reset the cursor before inserting actual text.
                self._set_cursor_valid()
            super().keyPressEvent(event)

    def insertFromMimeData(self, data:QMimeData) -> None:
        """ On a paste attempt, reset the cursor if necessary and paste only the plaintext content. """
        if data.hasText():
            self._set_cursor_valid()
            plaintext = QMimeData()
            plaintext.setText(data.text())
            super().insertFromMimeData(plaintext)


class TerminalDialog(QDialog):
    """ Qt terminal dialog tool. """

    DEFAULT_FLAGS = Qt.CustomizeWindowHint | Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowTitleHint

    def __init__(self, parent=None, flags=DEFAULT_FLAGS) -> None:
        super().__init__(parent, flags)
        self.setWindowTitle("Python Console")
        self.setMinimumSize(680, 480)
        self._w_text = TerminalTextWidget(self)
        layout = QVBoxLayout(self)
        layout.addWidget(self._w_text)

    def send(self, text:str) -> None:
        """ Send output text to the terminal. """
        self._w_text.write(text)

    def add_input_listener(self, on_input:InputCallback) -> None:
        """ Connect a callback to receive input text from the terminal. """
        self._w_text.lineEntered.connect(on_input)

    def add_interrupt_listener(self, on_interrupt:InterruptCallback) -> None:
        """ Connect a callback to receive interrupts from the terminal. """
        self._w_text.interrupted.connect(on_interrupt)

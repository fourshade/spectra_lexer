from io import TextIOBase
from typing import Callable

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


class StreamWriteAdapter(TextIOBase):
    """ Wraps a string callable in a text stream interface as write(). """

    def __init__(self, write:Callable[[str], None]) -> None:
        self._write = write

    def write(self, s:str) -> int:
        self._write(s)
        return len(s)

    def writable(self) -> bool:
        return True


class ConsoleTextWidget(QTextEdit):
    """ Formatted text widget meant to display plaintext interpreter input and output as a terminal.
        The text content is composed of two parts. The "base text" includes everything before the prompt.
        This is the terminal's saved history; it may be copied but not be edited.
        The "user text" comes after the prompt; it is freely modifiable by the user.
        When the user presses Enter, the user text is sent to the console, then frozen into the base text. """

    _FLAGS = Qt.TextSelectableByMouse | Qt.TextEditorInteraction

    _sig_text_out = pyqtSignal([str])  # Sent with a line of user input upon pressing Enter.
    _sig_text_in = pyqtSignal([str])   # Receives lines of console output.

    def __init__(self, *args, font=QFont("Courier New", 10)) -> None:
        super().__init__(*args)
        self._history = HistoryTracker()  # Tracks previous keyboard input.
        self._base_text = ""              # Unchangeable base text. User input may only appear after this.
        self.call_on_new_line = self._sig_text_out.connect
        self._sig_text_in.connect(self._add_text)
        self.setFont(font)
        self.setTextInteractionFlags(self._FLAGS)

    def to_stream(self) -> StreamWriteAdapter:
        """ Wrap this widget's input signal as a text stream. """
        return StreamWriteAdapter(self._sig_text_in.emit)

    def _add_text(self, text:str) -> None:
        """ Add to the base text of the widget. """
        self._base_text += text
        self._set_content(self._base_text)
        # To keep up with scrolling text, the vertical scroll position is fixed at the bottom.
        sy = self.horizontalScrollBar()
        sy.setValue(sy.maximum())

    def _set_content(self, text:str) -> None:
        """ Set new base text content and reset the cursor to the end. """
        self.setPlainText(text)
        c = self.textCursor()
        c.movePosition(QTextCursor.End)
        self.setTextCursor(c)

    def _set_cursor_valid(self) -> None:
        """ If the cursor is not within the current prompt, move it there. """
        min_position = len(self._base_text)
        c = self.textCursor()
        if c.position() < min_position:
            c.setPosition(min_position)
            self.setTextCursor(c)

    def keyPressEvent(self, event:QKeyEvent) -> None:
        """ Check the input for special cases. Make sure the cursor can't erase anything we started with. """
        self._set_cursor_valid()
        base_text = self._base_text
        # Up/down arrow keys will scroll through the command history.
        if event.key() == Qt.Key_Up:
            self._set_content(base_text + self._history.prev())
        elif event.key() == Qt.Key_Down:
            self._set_content(base_text + self._history.next())
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # If a newline is entered, capture only the user-provided text.
            # Add it to the history, append it to the base text (with newline), and send it in a signal.
            user_text = self.toPlainText()[len(base_text):]
            self._history.add(user_text)
            self._add_text(user_text + "\n")
            self._sig_text_out.emit(user_text)
        else:
            # In any other case, pass the keypress as normal. Undo anything that modifies the base text.
            super().keyPressEvent(event)
            if not self.toPlainText().startswith(base_text):
                self.undo()
            self._set_cursor_valid()

    def insertFromMimeData(self, data:QMimeData) -> None:
        """ On a paste attempt, reset the cursor if necessary and paste only the plaintext content. """
        if data.hasText():
            self._set_cursor_valid()
            plaintext = QMimeData()
            plaintext.setText(data.text())
            super().insertFromMimeData(plaintext)


class ConsoleDialog(ToolDialog):
    """ Qt console dialog window object. Routes signals between the console, a text widget, and the keyboard. """

    title = "Python Console"
    width = 680
    height = 480

    _console = None  # Saved console reference (to avoid garbage collection).

    def setup(self, locals_ns:dict) -> None:
        """ Create a new text widget and interpreter console instance. """
        w_text = ConsoleTextWidget(self)
        # Wrap the widget to appear as a text output stream to the console.
        self._console = SystemConsole(locals_ns, file=w_text.to_stream())
        self._console.print_opening()
        w_text.call_on_new_line(self._console.send)
        layout = QVBoxLayout(self)
        layout.addWidget(w_text)

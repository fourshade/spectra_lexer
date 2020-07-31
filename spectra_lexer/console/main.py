from PyQt5.QtCore import pyqtSignal

from . import introspect
from .qt import TerminalDialog
from .system import Console, TextIOWriter


def crop_text(text:str, max_chars:int, *, fillwidth=78) -> str:
    """ Crop <text> if larger than <max_chars>, replacing it with a filler row.
        Do not crop if the filler would *increase* the total text size. """
    cropcount = len(text) - max_chars
    if cropcount > fillwidth:
        half = max_chars // 2
        msg = f'[CROPPED {cropcount} CHARACTERS]'.center(fillwidth, '-')
        text = '\n'.join([text[:half], msg, text[-half:]])
    return text


class ConsoleDialog(TerminalDialog):
    """ Qt console dialog tool. Useful for live inspection of a Python object.
        All reads and writes are done with signals for thread safety. """

    _sig_write = pyqtSignal([str])  # Emitted to write output text using the main thread.
    _sig_close = pyqtSignal([])     # Emitted to close the dialog using the main thread.

    write_limit = 100000  # Maximum number of characters to add in one write without cropping.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._sig_write.connect(self.send)
        self._sig_close.connect(self.close)
        file_out = TextIOWriter(self._on_write)
        self._console = Console(file_out)
        self.add_input_listener(self._console.send)
        self.add_interrupt_listener(self._console.interrupt)

    def closeEvent(self, event) -> None:
        """ Force-stop the console thread on window close. """
        super().closeEvent(event)
        self._console.terminate()

    def _on_write(self, text:str) -> None:
        """ Write <text> to the window. Crop it first if too large. """
        text = crop_text(text, self.write_limit)
        self._sig_write.emit(text)

    def introspect(self, *args, **kwargs) -> None:
        """ Introspect a Python object in a new thread. Close the window when the thread exits. """
        def run() -> None:
            try:
                introspect(*args, **kwargs)
            finally:
                self._sig_close.emit()
        self._console.start(run)

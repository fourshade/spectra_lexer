from itertools import cycle
from traceback import TracebackException
from typing import Iterator

from PyQt5.QtCore import QTimer

from spectra_lexer.gui import TextDisplay


class GUIQtTextDisplay(TextDisplay):
    """ GUI Qt operations class for the text widget. Also shows status and exceptions. """

    w_title = resource("gui:w_display_title")  # Displays status messages and mapping of keys to word.
    w_text = resource("gui:w_display_text")    # Displays formatted rule graphs and other textual data.

    _anim: Iterator[str] = None  # Animation string iterator for the title bar. Should repeat.
    _title_timer: QTimer = None  # Animation timer for the title bar.

    @on("gui_load")
    def load(self) -> None:
        """ Connect the mouse command and set up the title bar animation timer. """
        self.w_text.textMouseAction.connect(self.on_click)
        self._title_timer = QTimer(self.w_title)
        self._title_timer.timeout.connect(self._animate_title)

    def _animate_title(self) -> None:
        """ Set the title to be the next item in the string iterator. """
        self.w_title.setText(next(self._anim))

    @on("new_status")
    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. If it ends in an ellipsis, animate it until a new status is shown. """
        if self._title_timer is not None:
            self._title_timer.stop()
            if s.endswith("..."):
                self._anim = cycle(map(s.strip(".").__add__, ["•..", ".•.", "..•", "..."]))
                self._title_timer.start(200)
        self.w_title.setText(s)

    def set_graph_text(self, text:str, **kwargs) -> None:
        """ Set the text content of the widget with HTML and mouse interactivity. """
        self.w_text.set_text(text, html=True, mouse=True, **kwargs)

    @on("exception")
    def exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to the main text widget, if possible. Return the exception if unsuccessful. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            self.w_text.set_text(tb_text)
        except Exception as e:
            return e

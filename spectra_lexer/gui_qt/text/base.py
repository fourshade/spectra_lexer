from itertools import cycle
from typing import Iterator

from PyQt5.QtCore import QTimer

from spectra_lexer.gui import TextDisplay
from spectra_lexer.utils import delegate_to


class GUIQtTextDisplay(TextDisplay):
    """ GUI Qt operations class for the text widget. """

    w_title = resource("gui:w_display_title", desc="Displays status messages and mapping of keys to word.")
    w_text = resource("gui:w_display_text", desc="Displays formatted rule graphs and other textual data.")

    _anim: Iterator[str] = None  # Animation string iterator for the title bar. Should repeat.
    _title_timer: QTimer = None  # Animation timer for the title bar.

    def load(self) -> None:
        """ Connect the mouse and set up the title bar animation timer. """
        self.w_text.textMouseAction.connect(self.on_click)
        self._title_timer = QTimer(self.w_title)
        self._title_timer.timeout.connect(self._animate_title)

    def _animate_title(self) -> None:
        """ Set the title to be the next item in the string iterator. """
        self.w_title.setText(next(self._anim))

    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. If it ends in an ellipsis, animate it until a new status is shown. """
        if self._title_timer is not None:
            self._title_timer.stop()
            if s.endswith("..."):
                self._anim = cycle(map(s.strip(".").__add__, ["•..", ".•.", "..•", "..."]))
                self._title_timer.start(200)
        self.w_title.setText(s)

    set_text = delegate_to("w_text")

from itertools import cycle
from typing import Sequence

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit


class TitleWidget(QLineEdit):
    """ Title bar widget that displays plaintext as well as simple text animations. """

    submitted = pyqtSignal([str])  # Emitted with the widget's current text when Enter is pressed.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._anim_timer = QTimer(self)  # Animation timer for loading messages.
        self.returnPressed.connect(self._on_submit_text)

    def _on_submit_text(self) -> None:
        """ Emit the widget text as a signal. """
        text = self.text()
        self.submitted.emit(text)

    def setText(self, text:str) -> None:
        """ Stop any animation and show normal text in the title bar. """
        self._anim_timer.stop()
        super().setText(text)

    def setAnimatedText(self, text_items:Sequence[str], delay_ms:int) -> None:
        """ Set the widget text to animate over <text_items> on a timed cycle.
            The first item is shown immediately, then a new one is shown every <delay_ms> milliseconds. """
        if text_items:
            show_next_item = map(super().setText, cycle(text_items)).__next__
            show_next_item()
            self._anim_timer.timeout.connect(show_next_item)
            self._anim_timer.start(delay_ms)

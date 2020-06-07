from itertools import cycle
from typing import Callable, Sequence

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QLineEdit


class DisplayTitle:
    """ Wrapper for title bar widget that displays plaintext as well as simple text animations. """

    def __init__(self, w_title:QLineEdit) -> None:
        self._w_title = w_title
        self._anim_timer = QTimer(w_title)  # Animation timer for loading messages.
        self._call_on_submit = None

    def _on_submit_text(self) -> None:
        """ Submit the title bar text to the callback. """
        text = self._w_title.text()
        self._call_on_submit(text)

    def connect_signals(self, on_edit:Callable[[str], None], on_submit:Callable[[str], None]) -> None:
        """ Connect Qt signals and set callback functions. """
        self._call_on_submit = on_submit
        self._w_title.textEdited.connect(on_edit)
        self._w_title.returnPressed.connect(self._on_submit_text)

    def set_enabled(self, enabled:bool) -> None:
        """ The title bar should be set read-only instead of disabled to continue showing status messages. """
        self._w_title.setReadOnly(not enabled)

    def set_static_text(self, text:str) -> None:
        """ Stop any animation and show normal text in the title bar. """
        self._anim_timer.stop()
        self._w_title.setText(text)

    def set_animated_text(self, text_items:Sequence[str], delay_ms:int) -> None:
        """ Set the widget text to animate over <text_items> on a timed cycle.
            The first item is shown immediately, then a new one is shown every <delay_ms> milliseconds. """
        if text_items:
            show_next_item = map(self._w_title.setText, cycle(text_items)).__next__
            show_next_item()
            self._anim_timer.timeout.connect(show_next_item)
            self._anim_timer.start(delay_ms)

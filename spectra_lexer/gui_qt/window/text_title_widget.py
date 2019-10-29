from itertools import cycle
from typing import Sequence

from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit


class TextTitleWidget(QLineEdit):
    """ Title bar widget that displays translations as well as loading/status with simple text animations.
        Also allows manual lexer queries by editing translations directly. """

    TRANSLATION_DELIM = " -> "  # Delimiter between keys and letters of translations shown in title bar.

    sig_edit_translation = pyqtSignal([list])  # Sent with a [keys, letters] translation on a valid edit.

    def __init__(self, *args) -> None:
        """ Set up the animation timer. It should stop ongoing animations when the text changes by external means. """
        super().__init__(*args)
        self._anim_iter= cycle([""])  # Animation string iterator. Should repeat indefinitely.
        self._timer = QTimer(self)    # Animation timer for loading messages.
        self._timer.timeout.connect(self._animate)
        self.textChanged.connect(self._timer.stop)
        self.textEdited.connect(self._edit_translation)

    def _edit_translation(self, text:str) -> None:
        """ Parse the title bar text as a translation and send the signal if it is valid. """
        parts = text.split(self.TRANSLATION_DELIM)
        if len(parts) == 2:
            translation = [p.strip() for p in parts]
            self.sig_edit_translation.emit(translation)

    def set_translation(self, translation:list) -> None:
        """ Format a translation and show it in the title bar. """
        self.setText(self.TRANSLATION_DELIM.join(translation))

    def set_status(self, text:str) -> None:
        """ Check if the status text ends in an ellipsis. If not, just show the text normally.
            Otherwise, animate the text with a • dot moving down the ellipsis until new text is shown:
            loading...  ->  loading•..  ->  loading.•.  ->  loading..• """
        if text.endswith("..."):
            body = text.rstrip(".")
            frames = [body + b for b in ("...", "•..", ".•.", "..•")]
            self._animate_text(frames, 200)
        else:
            self.setText(text)

    def _animate_text(self, text_items:Sequence[str], delay_ms:int) -> None:
        """ Set the widget text to animate over <text_items> on a timed cycle.
            The first item is shown immediately, then a new one is shown every <delay_ms> milliseconds. """
        if text_items:
            self._anim_iter = cycle(text_items)
            self._animate()
            self._timer.start(delay_ms)

    def _animate(self) -> None:
        """ Set the widget text to the next item in the string iterator. Block the timer stop signal here. """
        text = next(self._anim_iter)
        self.blockSignals(True)
        self.setText(text)
        self.blockSignals(False)

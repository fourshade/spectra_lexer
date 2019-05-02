from functools import partial
from itertools import cycle
import sys
from traceback import TracebackException
from typing import Iterator

from PyQt5.QtCore import QTimer

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtTextDisplay(Component):
    """ GUI operations class for displaying status, interactive text, and exceptions.
        Also handles mouse input to the text widget. """

    w_title = resource("gui:w_display_title", desc="Displays status messages and mapping of keys to word.")
    w_text = resource("gui:w_display_text", desc="Displays formatted rule graphs and other textual data.")
    _anim: Iterator[str] = None  # Animation string iterator for the title bar. Should repeat.
    _title_timer: QTimer = None  # Animation timer for the title bar.

    @on("load_gui")
    def load(self) -> None:
        """ Connect the mouse signal to the main text window and set up the animation timer. """
        self.w_text.textMouseAction.connect(partial(self.engine_call, "text_mouse_action"))
        self._title_timer = QTimer(self.w_title)
        self._title_timer.timeout.connect(self.animate_title)

    @on("new_status")
    @on("new_title_text")
    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. If it ends in an ellipsis, animate it until a new status is shown. """
        if self._title_timer is not None:
            self._title_timer.stop()
            if s.endswith("..."):
                self._anim = cycle(map(s.strip(".").__add__, ["•..", ".•.", "..•", "..."]))
                self._title_timer.start(200)
        self.w_title.setText(s)

    def animate_title(self) -> None:
        """ Set the title to be the next item in the string iterator. """
        self.w_title.setText(next(self._anim))

    set_text = delegate_to("w_text")
    set_graph_text = on("new_graph_text")(delegate_to("w_text"))

    @on("exception")
    def handle_exception(self, e:Exception) -> bool:
        """ Format and print an exception using the first available print method. """
        tb_lines = TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        # Plover owns stderr while running, and the GUI can only print exceptions after setup.
        # To avoid crashing Plover, only report failure if NONE of the possible print methods succeed.
        for obj, attr in [(self, "set_text"), (sys.stderr, "write")]:
            try:
                getattr(obj, attr)(tb_text)
                return True
            except Exception:
                pass
        return False

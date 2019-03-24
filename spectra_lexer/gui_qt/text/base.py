from functools import partial
import sys
from traceback import TracebackException

from spectra_lexer import Component
from spectra_lexer.utils import delegate_to


class GUIQtTextDisplay(Component):
    """ GUI operations class for displaying status, interactive text, and exceptions.
        Also handles keyboard and mouse input to the text widget. """

    w_title = Resource("gui", "w_display_title", None, "Displays status messages and mapping of keys to word.")
    w_text = Resource("gui",  "w_display_text",  None, "Displays formatted rule graphs and other textual data.")

    @on("load_gui")
    def load(self) -> None:
        """ Connect the keyboard and mouse signals to the main text window. """
        self.w_text.textMouseAction.connect(partial(self.engine_call, "text_mouse_action"))
        self.w_text.textKeyboardInput.connect(partial(self.engine_call, "text_keyboard_input"))

    set_title = on("new_status")(on("new_title_text")(delegate_to("w_title.setText")))

    set_interactive_text = on("new_interactive_text")(delegate_to("w_text"))

    @on("exception")
    def handle_exception(self, e:Exception) -> bool:
        """ Unlike other commands, this one can arrive before the widgets are set up. Check them first.
            To avoid crashing Plover, exceptions are suppressed (by returning True) after display. """
        tb_lines = TracebackException.from_exception(e).format()
        tb_text = "".join(tb_lines)
        sys.stderr.write(tb_text)
        if self.w_text is not None:
            self.w_text.set_interactive_text(tb_text)
        return True

from .base import GUIQT


class QtGraph(GUIQT):
    """ Qt implementation class for the text widget. Also shows status and exceptions. """

    _last_status: str = ""

    def GUIQTConnect(self) -> None:
        """ Connect the mouse command and display the last status if it occurred before connection. """
        self.W_TEXT.textMouseAction.connect(self.graph_action)
        self._set_title(self._last_status)

    def VIEWNewTitle(self, s:str) -> None:
        """ Set the text in the title bar. """
        self._set_title(s)

    def VIEWNewGraph(self, text:str, **kwargs) -> None:
        """ Set the text content of the widget with HTML and mouse interactivity. """
        self.W_TEXT.set_interactive_text(text, **kwargs)

    def SYSStatus(self, status:str) -> None:
        """ Show engine status messages in the title as well. Save the last one in case we're not connected yet. """
        self._set_title(status)
        self._last_status = status

    def SYSTraceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget, if possible. """
        try:
            self._set_title("Well, this is embarrassing...", dynamic=False)
            self.W_TEXT.set_plaintext(tb_text)
        except Exception:
            # The Qt GUI is probably what raised the error in the first place.
            # Re-raising will kill the program. Let lower-level handlers try first.
            pass

    def _set_title(self, s:str, **kwargs):
        if self.W_TITLE is not None:
            self.W_TITLE.set_text(s, **kwargs)

from .base import GUIQT


class QtStatus(GUIQT):
    """ Qt implementation class for status and exceptions. """

    _last_status: str = ""

    def GUIQTConnect(self) -> None:
        """ Display the last status if it occurred before connection. """
        if self._last_status:
            self.W_TITLE.set_text(self._last_status)

    def SYSStatus(self, status:str) -> None:
        """ Show engine status messages in the title as well. Save the last one in case we're not connected yet. """
        if self.W_TITLE is not None:
            self.W_TITLE.set_text(status)
        else:
            self._last_status = status

    def SYSTraceback(self, tb_text:str) -> None:
        """ Print an exception traceback to the main text widget, if possible. """
        try:
            self.W_TITLE.set_text("Well, this is embarrassing...", dynamic=False)
            self.W_TEXT.set_plaintext(tb_text)
        except Exception:
            # The Qt GUI is probably what raised the error in the first place.
            # Re-raising will kill the program. Let lower-level handlers try first.
            pass

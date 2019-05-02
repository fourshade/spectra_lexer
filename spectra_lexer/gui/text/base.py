import sys
from traceback import TracebackException

from spectra_lexer import Component


class TextDisplay(Component):
    """ GUI operations class for displaying status, text, exceptions, and mouse input. """

    @on("load_gui")
    def load(self) -> None:
        """ Connect the command to send mouse input on click. """
        raise NotImplementedError

    def on_click(self, row:int, col:int, clicked:bool=False) -> None:
        """ Call this command with the cursor character position and mouse button state. """
        self.engine_call("text_mouse_action", row, col, clicked)

    @on("new_status")
    @on("new_title_text")
    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. """
        raise NotImplementedError

    def set_text(self, text:str, *, html:bool=False, mouse:bool=False, scroll_to:str="top") -> None:
        """ Set the text content of the widget and <scroll_to> the top or bottom (or don't if scroll_to=None). """
        raise NotImplementedError

    @on("new_graph_text")
    def set_graph_text(self, text:str, **kwargs) -> None:
        """ Set the text content of the widget with HTML and mouse interactivity. """
        self.set_text(text, html=True, mouse=True, **kwargs)

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

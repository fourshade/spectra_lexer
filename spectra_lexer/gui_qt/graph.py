import sys
from traceback import TracebackException

from .window import GUI
from spectra_lexer.core import Component, COREApp, COREEngine
from spectra_lexer.system import SYSControl
from spectra_lexer.view import VIEWGraph


class QtGraph(Component, SYSControl,
              GUI.DisplayTitle, GUI.DisplayGraph,
              COREApp.Start, COREEngine.Exception, VIEWGraph.NewTitle, VIEWGraph.NewGraph):
    """ Qt implementation class for the text widget. Also shows status and exceptions. """

    def on_app_start(self) -> None:
        """ Connect the mouse command. """
        self.w_text.textMouseAction.connect(self._on_mouse_action)

    def _on_mouse_action(self, row:int, col:int, clicked:bool) -> None:
        """ When the mouse moves over a new character and/or is clicked,
            call a command with the row/column character position. """
        cmd = VIEWGraph.select_character if clicked else VIEWGraph.hover_character
        self.engine_call(cmd, row, col)

    def on_graph_title(self, s:str) -> None:
        """ Set the text in the title bar. """
        self.w_title.set_text(s)

    def on_graph_output(self, text:str, **kwargs) -> None:
        """ Set the text content of the widget with HTML and mouse interactivity. """
        self.w_text.set_interactive_text(text, **kwargs)

    # Show engine status messages in the title as well.
    status = on_graph_title

    def exit(self) -> None:
        sys.exit()

    def on_engine_exception(self, exc_value:Exception) -> Exception:
        """ Print an exception traceback to the main text widget, if possible. Return the exception if unsuccessful. """
        tb_lines = TracebackException.from_exception(exc_value).format()
        tb_text = "".join(tb_lines)
        try:
            self.w_title.set_text("Well, this is embarrassing...", dynamic=False)
            self.w_text.set_plaintext(tb_text)
        except Exception as e:
            return e

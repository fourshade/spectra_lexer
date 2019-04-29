from spectra_lexer.core import Component


class TextDisplay(Component):
    """ GUI operations class for handling text graphs and mouse input. """

    def on_click(self, row:int, col:int, clicked:bool=False) -> None:
        """ Call this command with the cursor character position and mouse button state. """
        self.engine_call("text_mouse_action", row, col, clicked)

    @on("new_title_text")
    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. """
        raise NotImplementedError

    @on("new_graph_text")
    def set_graph_text(self, text:str, scroll_to:str="top") -> None:
        """ Set the main graph text and <scroll_to> the top or bottom (or don't if scroll_to=None). """
        raise NotImplementedError

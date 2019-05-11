from spectra_lexer.core import Component


class TextDisplay(Component):
    """ GUI operations class for handling text graphs and mouse input. """

    def on_mouse_move(self, row:int, col:int, clicked:bool=False) -> None:
        """ When the mouse moves over a new character and/or is clicked,
            call this method with the row/column character position and button state. """
        self.engine_call("text_mouse_action", row, col, clicked)

    @on("new_title_text")
    def set_title(self, s:str) -> None:
        """ Set the text in the title bar. """
        raise NotImplementedError

    @on("new_graph_text")
    def set_graph_text(self, text:str, scroll_to:str="top") -> None:
        """ Set the HTML graph text and <scroll_to>: the "top", the "bottom", or don't scroll if None. """
        raise NotImplementedError

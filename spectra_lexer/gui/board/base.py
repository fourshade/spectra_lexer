from typing import List

from spectra_lexer.core import Component


class BoardDisplay(Component):
    """ Interface to draw steno board diagram elements and the description for rules. """

    _last_link_ref: str = ""  # Name for the most recent rule with examples in the index.

    def on_link(self) -> None:
        """ Call this when the examples link is clicked to send a search query. """
        self.engine_call("board_find_examples", self._last_link_ref)

    def on_resize(self, width:int, height:int) -> None:
        """ Call this to notify the board layout engine when the board's graphical container changes size. """
        self.engine_call("board_set_size", width, height)

    @on_resource("system:board")
    def set_board(self, board:dict) -> None:
        self.set_xml(board["raw"])

    def set_xml(self, xml:bytes) -> None:
        """ Set the current raw XML string that represents the available elements to draw. """
        raise NotImplementedError

    @on("new_board_info")
    def set_board_info(self, caption:str, link_ref:str="") -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner.
            The link reference must be remembered in order to find the right rule examples. """
        self._last_link_ref = link_ref
        self.set_caption(caption)
        self.set_link_enabled(bool(link_ref))

    def set_caption(self, caption:str) -> None:
        """ Set the current plaintext caption for the board. """
        raise NotImplementedError

    def set_link_enabled(self, enabled:bool) -> None:
        """ Set whether or not the link to examples is shown. """
        raise NotImplementedError

    @on("new_board_layout")
    def set_layout(self, element_info:List[tuple]) -> None:
        """ Set the currently displayed graphical element IDs along with their positions and scales. """
        raise NotImplementedError

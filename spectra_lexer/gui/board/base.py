from typing import List

from spectra_lexer.core import Component


class BoardDisplay(Component):
    """ Interface to draw steno board diagram elements and the description for rules. """

    def on_link(self, rule_name:str) -> None:
        """ Connect the command to send link info on click. """
        self.engine_call("board_find_examples", rule_name)

    def on_resize(self, width:int, height:int) -> None:
        """ Connect the command to send the board display size on GUI resize. """
        self.engine_call("board_set_size", width, height)

    @on_resource("system:board")
    def set_board(self, board:dict) -> None:
        self.set_xml(board["raw"])

    def set_xml(self, xml:bytes) -> None:
        raise NotImplementedError

    @on("new_board_caption")
    def set_caption(self, caption:str, link_ref:str="") -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner. """
        raise NotImplementedError

    @on("new_board_layout")
    def set_layout(self, element_info:List[tuple]) -> None:
        raise NotImplementedError

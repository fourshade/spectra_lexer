from typing import List

from spectra_lexer import Component


class BoardDisplay(Component):
    """ Interface to draw steno board diagram elements and the description for rules. """

    @on("load_gui")
    def load(self) -> None:
        """ Connect the commands to send link info on click and the board widget size on resize. """
        raise NotImplementedError

    def on_link(self, rule_name:str) -> None:
        self.engine_call("board_find_examples", rule_name)

    def on_resize(self, width:int, height:int) -> None:
        self.engine_call("board_set_size", width, height)

    @on("new_board_caption")
    def set_caption(self, caption:str, link_ref:str="") -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner. """
        raise NotImplementedError

    @on("new_board_xml")
    def set_xml(self, xml:bytes) -> None:
        raise NotImplementedError

    @on("new_board_layout")
    def set_layout(self, element_info:List[tuple]) -> None:
        raise NotImplementedError

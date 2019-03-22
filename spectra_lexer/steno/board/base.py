""" Module for generating steno board diagram elements and descriptions. """

from typing import Dict, List, Tuple

from .caption import CaptionGenerator
from .layout import ElementLayout
from .matcher import ElementMatcher
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.utils import delegate_to


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    show_compound = Resource("config", "board:show_compound_keys", True,
                             "Show special labels for compound keys (i.e. `f` instead of TP) and numbers")
    show_links = Resource("config", "board:show_example_links", True,
                          "Show hyperlinks to other examples of a selected rule. Requires an index.")

    _captioner: CaptionGenerator     # Generates the caption text above the board diagram.
    _matcher: ElementMatcher         # Generates the list of element IDs for each stroke of a rule.
    _layout: ElementLayout = None    # Calculates drawing bounds for each element.
    _last_ids: List[List[str]] = []  # Last set of element IDs, saved in case of resizing.

    def __init__(self) -> None:
        """ Set up the captioner and matcher with empty dictionaries. """
        super().__init__()
        self._captioner = CaptionGenerator()
        self._matcher = ElementMatcher()

    @on("new_board", pipe_to="new_board_xml")
    def set_board(self, raw:str, ids:Dict[str, dict]) -> Tuple[str, Dict[str, dict]]:
        """ Save element ID names to the matcher. """
        self._matcher.set_ids(ids)
        # Send the raw SVG text data along with all element IDs to the GUI.
        return raw, ids

    @on("new_rules")
    def set_rules(self, d:dict):
        self._captioner.set_rules(d)
        self._matcher.set_rules(d)

    set_index = on("new_index")(delegate_to("_captioner"))

    @on("board_set_view", pipe_to="new_board_layout")
    def set_layout(self, view_box:tuple, width:int, height:int) -> List[tuple]:
        """ Set the viewbox and the layout's max bounds if non-zero. Recompute the current layout and send it. """
        if all(view_box[2:3]) and width and height:
            self._layout = ElementLayout(view_box, width, height)
            return self._layout.make_draw_list(self._last_ids)

    @on("new_output", pipe_to="new_board_layout")
    @on("new_graph_selection", pipe_to="new_board_layout")
    def get_info(self, rule:StenoRule) -> List[tuple]:
        """ Generate board diagram layouts from a steno rule and send them along with a caption and/or example link.
            The task is identical whether the rule is from a new output or a user graph selection. """
        caption = self._captioner.get_text(rule)
        link_params = self._captioner.get_link(rule) if self.show_links else ()
        self.engine_call("new_board_caption", caption, *link_params)
        # Create the element ID lists (one list for each stroke) with or without the special elements and draw them.
        self._last_ids = self._matcher.get_element_ids(rule, self.show_compound)
        if self._layout is not None:
            return self._layout.make_draw_list(self._last_ids)

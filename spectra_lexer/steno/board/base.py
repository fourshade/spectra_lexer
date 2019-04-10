""" Module for generating steno board diagram elements and descriptions. """

from typing import List

from .caption import CaptionGenerator
from .layout import ElementLayout
from .matcher import ElementMatcher
from spectra_lexer import Component
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.system import StenoSystem
from spectra_lexer.utils import delegate_to


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    show_compound = Resource("config", "board:show_compound_keys", True,
                             "Show special labels for compound keys (i.e. `f` instead of TP) and numbers")
    show_links = Resource("config", "board:show_example_links", True,
                          "Show hyperlinks to other examples of a selected rule. Requires an index.")

    _captioner: CaptionGenerator     # Generates the caption text above the board diagram.
    _layout: ElementLayout           # Calculates drawing bounds for each element.
    _matcher: ElementMatcher = None  # Generates the list of element IDs for each stroke of a rule.
    _last_rule: StenoRule = None     # Last diagrammed rule, saved in case of resizing or example requests.

    def __init__(self):
        """ Set up an empty captioner and layout. """
        super().__init__()
        self._captioner = CaptionGenerator()
        self._layout = ElementLayout()

    set_index = on("set_dict_index")(delegate_to("_captioner"))

    @on("set_system", pipe_to="new_board_xml")
    def set_system(self, system:StenoSystem) -> bytes:
        """ The first SVG element with an ID and a viewbox is the root element. Set the layout's viewbox from this. """
        root = next(d for d in system.board["id"].values() if "viewBox" in d)
        self._layout.set_view(tuple(map(int, root["viewBox"].split())))
        # Create the matcher with the system and send the raw SVG XML data to the GUI.
        self._matcher = ElementMatcher(system)
        self._captioner.set_rules_reversed(system.rev_rules)
        return system.board["raw"]

    @on("board_set_size", pipe_to="new_board_layout")
    def set_size(self, width:int, height:int) -> List[tuple]:
        """ Set the layout's maximum dimensions. Recompute the current layout and send it. """
        self._layout.set_size(width, height)
        if self._last_rule is not None:
            return self.get_info(self._last_rule)

    @on("new_output", pipe_to="new_board_layout")
    @on("new_graph_selection", pipe_to="new_board_layout")
    def get_info(self, rule:StenoRule) -> List[tuple]:
        """ Generate board diagram layouts from a steno rule and send them along with a caption and/or example link.
            The task is identical whether the rule is from a new output or a user graph selection. """
        self._last_rule = rule
        caption = self._captioner.get_text(rule)
        link_ref = self._captioner.get_link_ref(rule) if self.show_links else ""
        self.engine_call("new_board_caption", caption, link_ref)
        # Create the element ID lists (one list for each stroke) with or without the special elements and draw them.
        if self._matcher is not None:
            ids = self._matcher.get_element_ids(rule, self.show_compound)
            return self._layout.make_draw_list(ids)

    @on("board_find_examples", pipe_to="search_examples")
    def get_examples(self, name:str) -> tuple:
        """ If the link on the diagram is clicked, get a random translation using this rule and search near it. """
        return (name, self._last_rule, *self._captioner.get_random_example(name))

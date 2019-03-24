""" Module for generating steno board diagram elements and descriptions. """

from typing import Dict, List, Tuple

from .caption import CaptionGenerator
from .layout import ElementLayout
from .matcher import ElementMatcher
from spectra_lexer import Component
from spectra_lexer.file import XML
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.utils import delegate_to, save_kwargs


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    file = Resource("cmdline", "board-file", ":/board.svg", "SVG file with graphics for the steno board diagram.")
    show_compound = Resource("config", "board:show_compound_keys", True,
                             "Show special labels for compound keys (i.e. `f` instead of TP) and numbers")
    show_links = Resource("config", "board:show_example_links", True,
                          "Show hyperlinks to other examples of a selected rule. Requires an index.")

    _captioner: CaptionGenerator     # Generates the caption text above the board diagram.
    _matcher: ElementMatcher = None  # Generates the list of element IDs for each stroke of a rule.
    _layout: ElementLayout = None    # Calculates drawing bounds for each element.
    _last_rule: StenoRule = None     # Last diagrammed rule, saved in case of resizing or example requests.

    def __init__(self):
        """ Set up the captioner and matcher with empty dictionaries. """
        super().__init__()
        self._captioner = CaptionGenerator()

    set_index = on("set_dict_index")(delegate_to("_captioner"))
    set_rules_reversed = on("set_dict_rules_reversed")(delegate_to("_captioner"))

    @on("load_dicts", pipe_to="new_board_xml")
    @on("board_load", pipe_to="new_board_xml")
    def load(self, filename:str="") -> Tuple[str, Dict[str, dict]]:
        """ Load an SVG file and send the raw SVG text data along with all element IDs to the GUI. """
        d = XML.load(filename or self.file)
        self._load_matcher(ids=d["ids"])
        return d["raw"], d["ids"]

    @on("set_dict_rules")
    def set_rules(self, d:dict) -> None:
        self._load_matcher(rules=d)

    @save_kwargs
    def _load_matcher(self, rules:dict=None, ids:dict=None) -> None:
        """ Create the matcher when the rules and element IDs are both ready. """
        if rules and ids:
            self._matcher = ElementMatcher(rules, ids)

    @on("board_set_view", pipe_to="new_board_layout")
    def set_layout(self, view_box:tuple, width:int, height:int) -> List[tuple]:
        """ Set the viewbox and the layout's max bounds if non-zero. Recompute the current layout and send it. """
        if all(view_box[2:3]) and width and height:
            self._layout = ElementLayout(view_box, width, height)
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
        if self._layout is not None and self._matcher is not None:
            ids = self._matcher.get_element_ids(rule, self.show_compound)
            return self._layout.make_draw_list(ids)

    @on("board_find_examples", pipe_to="search_examples")
    def get_examples(self, name:str) -> tuple:
        """ If the link on the diagram is clicked, get a random translation using this rule and search near it. """
        return (name, self._last_rule, *self._captioner.get_random_example(name))

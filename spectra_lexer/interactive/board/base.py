""" Module for generating steno board diagram elements and descriptions. """

from typing import Dict, List, Tuple
from xml.parsers.expat import ParserCreate

from spectra_lexer import Component, on, pipe
from spectra_lexer.config import CFGOption
from spectra_lexer.interactive.board.layout import ElementLayout
from spectra_lexer.interactive.board.matcher import ElementMatcher
from spectra_lexer.rules import RuleFlags, StenoRule

# Resource identifier for the main SVG graphic. Contains every element needed.
_BOARD_ASSET_NAME = ':/board.svg'


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    ROLE = "board"
    show_compound: bool = CFGOption(True, "Compound Key Labels", "Show special labels for compound keys and numbers")

    _matcher: ElementMatcher         # Generates the list of element IDs for each stroke of a rule.
    _layout: ElementLayout = None    # Calculates drawing bounds for each element.
    _last_ids: List[List[str]] = []  # Last set of element IDs, saved in case of resizing.

    def __init__(self) -> None:
        """ Set up the matcher with an empty rule dictionary and the layout with default coordinates. """
        super().__init__()
        self._matcher = ElementMatcher()

    @pipe("start", "board_load")
    def start(self, board:str=None, **opts) -> str:
        """ If there is a command line option for this component, even if empty, attempt to load an SVG.
            If the option is present but empty (or otherwise evaluates False), use the default instead. """
        if board is not None:
            return board or ()

    @pipe("board_load", "new_board_setup")
    def load(self, filename:str=_BOARD_ASSET_NAME) -> Tuple[str, List[str]]:
        """ Load and parse element ID names out of the raw XML string data. """
        xml_dict = self.engine_call("file_load", filename)
        id_dict = {}
        def start_element(name, attrs):
            if "id" in attrs:
                attrs["name"] = name
                id_dict[attrs["id"]] = attrs
        p = ParserCreate()
        p.StartElementHandler = start_element
        p.Parse(xml_dict["raw"])
        self._matcher.set_ids(id_dict)
        # Send the raw SVG text data along with all element IDs to the GUI.
        return xml_dict["raw"], list(id_dict)

    @on("new_rules")
    def set_rules(self, rules_dict:Dict[str,StenoRule]) -> None:
        """ Set up the matcher with the rule dictionary. """
        self._matcher.set_rules(rules_dict)

    @pipe("board_set_layout", "new_board_gfx")
    def set_layout(self, view_box:tuple, width:int, height:int) -> List[tuple]:
        """ Set the viewbox and the layout's max bounds. Recompute the current layout and send it. """
        self._layout = ElementLayout(view_box, width, height)
        return self._layout.make_draw_list(self._last_ids)

    @pipe("new_lexer_result", "new_board_gfx")
    def get_info(self, rule:StenoRule) -> List[tuple]:
        """ Generate board diagram graphics from a steno rule and send them along with the description. """
        self.engine_call("new_board_description", _get_description(rule))
        # Create the element ID lists (one list for each stroke) with or without the special elements and draw them.
        self._last_ids = self._matcher.get_element_ids(rule, self.show_compound)
        if self._layout is not None:
            return self._layout.make_draw_list(self._last_ids)

    @pipe("new_graph_selection", "new_board_gfx")
    def get_selection_info(self, rule:StenoRule) -> List[tuple]:
        """ The task is identical whether the rule is from a new lexer result or a user graph selection. """
        return self.get_info(rule)


def _get_description(rule:StenoRule) -> str:
    """ Generate a caption text for a rule to go above the board diagram. """
    description = rule.desc
    # If this is a lexer-generated rule (usually the root at the top), just display the description by itself.
    if RuleFlags.GENERATED in rule.flags:
        return description
    # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
    raw_keys = rule.keys.rtfcre
    if not rule.rulemap:
        return "{}: {}".format(raw_keys, description)
    # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
    return "{} → {}: {}".format(raw_keys, rule.letters, description)

""" Module for generating steno board diagram elements and descriptions. """

from .caption import CaptionGenerator
from .layout import ElementLayout
from .matcher import ElementMatcher
from spectra_lexer.core import Component
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.system import StenoSystem
from spectra_lexer.types import delegate_to


class BoardRenderer(Component):
    """ Creates graphics and description strings for the board diagram. """

    show_compound = resource("config:board:show_compound_keys", True,
                             desc="Show special labels for compound keys (i.e. `f` instead of TP) and numbers")
    show_links = resource("config:board:show_example_links", True,
                          desc="Show hyperlinks to other examples of a selected rule. Requires an index.")

    _captioner: CaptionGenerator     # Generates the caption text above the board diagram.
    _layout: ElementLayout           # Calculates drawing bounds for each element.
    _matcher: ElementMatcher = None  # Generates the list of element IDs for each stroke of a rule.
    _last_rule: StenoRule = None     # Last diagrammed rule, saved in case of resizing or example requests.

    def __init__(self):
        """ Set up an empty captioner and layout. """
        super().__init__()
        self._captioner = CaptionGenerator()
        self._layout = ElementLayout()

    set_index = on_resource("index")(delegate_to("_captioner"))

    @on_resource("system")
    def set_system(self, system:StenoSystem) -> None:
        """ The first <svg> element with a viewbox is the root element. Set the layout's viewbox to match it. """
        root = system.board["name"]["svg"]
        if root:
            self._layout.set_view(tuple(map(int, root[0]["viewBox"].split())))
        # Create the matcher with the system and send the raw SVG XML data to the GUI.
        self._matcher = ElementMatcher(system)
        self._captioner.set_rules_reversed(system.rev_rules)

    @on("board_set_size")
    def set_size(self, width:int, height:int) -> None:
        """ Set the layout's maximum dimensions. Recompute the current layout and send it. """
        self._layout.set_size(width, height)
        if self._last_rule is not None:
            self.display_rule(self._last_rule)

    @on("board_display_rule")
    def display_rule(self, rule:StenoRule) -> None:
        """ Generate board diagram layouts from a steno rule and send them along with a caption and/or example link.
            The task is identical whether the rule is from a new output or a user graph selection. """
        self._last_rule = rule
        caption = self._captioner.get_text(rule)
        link_ref = self._captioner.get_link_ref(rule) if self.show_links else ""
        self.engine_call("new_board_caption", caption, link_ref)
        # Create the element ID lists (one list for each stroke) with or without the special elements and draw them.
        if self._matcher is not None:
            ids = self._matcher.get_element_ids(rule, self.show_compound)
            self.engine_call("new_board_layout", self._layout.make_draw_list(ids))

    @on("board_find_examples")
    def find_examples(self, rule_name:str) -> None:
        """ If the link on the diagram is clicked, get a random translation using this rule and search near it. """
        self.engine_call("search_examples", rule_name, self._last_rule, *self._captioner.get_random_example(rule_name))

""" Module for generating steno board diagram elements and descriptions. """

from typing import Dict, List, Tuple

from spectra_lexer import on, pipe
from spectra_lexer.board.generator import BoardGenerator
from spectra_lexer.config import Configurable, CFGOption
from spectra_lexer.rules import RuleFlags, StenoRule


class BoardRenderer(Configurable):
    """ Creates graphics and description strings for the board diagram. """

    ROLE = "board"
    show_compound: bool = CFGOption(True, "Compound Key Labels", "Show special labels for compound keys and numbers")

    _generator: BoardGenerator = None  # Generates the list of elements for each stroke of a rule.

    @on("new_rules")
    def set_rules(self, rules_dict:Dict[str,StenoRule]) -> None:
        """ Set up the generator with the rule dictionary. """
        self._generator = BoardGenerator(rules_dict)

    @on("new_board")
    def set_elements(self, xml_dict:dict) -> None:
        """ Load the generator with each graphical element that has a specific rule. """
        self._generator.set_rule_elements(xml_dict)

    @pipe("new_lexer_result", "new_board_info", unpack=True)
    def make_board_from_rule(self, rule:StenoRule) -> Tuple[List[List[str]],str]:
        """ Generate board diagram elements from a steno rule and send them along with the description. """
        keys, letters, flags, desc, rulemap = rule
        raw_keys = keys.to_rtfcre()
        if RuleFlags.GENERATED in flags:
            # If this is a lexer-generated rule (usually the root at the top), just display the description.
            description = desc
        elif not rulemap:
            # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
            description = "{}: {}".format(raw_keys, desc)
        else:
            # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
            description = "{} → {}: {}".format(raw_keys, letters, desc)
        # Create the list of element lists (one list for each stroke), with or without the special rule elements.
        elements = self._generator.generate(rule, self.show_compound)
        return elements, description

    @pipe("new_graph_selection", "new_board_info", unpack=True)
    def make_board_from_node(self, rule:StenoRule) -> Tuple[List[List[str]],str]:
        """ The task is identical whether the rule is from a new lexer result or a user graph selection. """
        return self.make_board_from_rule(rule)

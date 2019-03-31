import random
from typing import Dict, Union

from spectra_lexer.steno.rules import RuleFlags, StenoRule


class CaptionGenerator:
    """ Generates captions for the board diagram along with optional links to examples from an index. """

    _index: Dict[str, Union[list, dict]] = {}  # Index of example translations by rule name, in either form.
    _rev_rules: Dict[StenoRule, str] = {}      # Dict of rule objects mapped to their reference names.

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Make a shallow copy of the index so we can replace dicts with lists incrementally. """
        self._index = dict(index)

    def set_rules_reversed(self, rd:Dict[StenoRule, str]) -> None:
        """ Set up a dict with rules as keys and their names as values. """
        self._rev_rules = rd

    def get_text(self, rule:StenoRule) -> str:
        """ Generate a plaintext caption for a rule based on its position in the current tree. """
        description = rule.desc
        # If this is the root rule at the top, the title shows the keys. Just display the description by itself.
        # Save its keys and letters for later use in links.
        if RuleFlags.GENERATED in rule.flags:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        keys = rule.keys
        if not rule.rulemap:
            return f"{keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{keys} → {rule.letters}: {description}"

    def get_link_ref(self, rule:StenoRule) -> str:
        """ Look for the current rule's name. If there are examples in the index, return the name reference. """
        name = self._rev_rules.get(rule)
        if name in self._index:
            return name
        return ""

    def get_random_example(self, name:str) -> tuple:
        """ Find an index for a rule by name and return one translation from it at random.
            The index must be a list to do this. If it isn't one, convert it and store it back. """
        obj = self._index[name]
        if isinstance(obj, dict):
            obj = self._index[name] = list(obj.items())
        return random.choice(obj)

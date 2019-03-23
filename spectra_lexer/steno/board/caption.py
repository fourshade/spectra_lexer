import random
from typing import Dict

from spectra_lexer.steno.rules import RuleFlags, StenoRule


class CaptionGenerator:
    """ Generates captions for the board diagram along with optional links to examples from an index. """

    _examples: Dict[StenoRule, tuple] = {}  # Index of example translations by rule object.

    def set_examples(self, rules:Dict[str, StenoRule], index:Dict[str, dict]) -> None:
        """ Set up the examples dict with rules as keys and names+lists as values. """
        self._examples = {rules.get(n): (n, list(d.items())) for n, d in index.items()}

    def get_text(self, rule:StenoRule) -> str:
        """ Generate a plaintext caption for a rule based on its position in the current tree. """
        description = rule.desc
        # If this is the root rule at the top, the title shows the keys. Just display the description by itself.
        # Save its keys and letters for later use in links.
        if RuleFlags.GENERATED in rule.flags:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        raw_keys = rule.keys.rtfcre
        if not rule.rulemap:
            return f"{raw_keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{raw_keys} → {rule.letters}: {description}"

    def get_link(self, rule:StenoRule) -> tuple:
        """ Look for the current rule in the index. If there are examples, return one at random. """
        name, seq = self._examples.get(rule, (None, None))
        if not name:
            return ()
        return (name, rule, *random.choice(seq))

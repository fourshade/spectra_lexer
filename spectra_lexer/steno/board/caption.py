from typing import Dict

from spectra_lexer.steno.rules import RuleFlags, StenoRule


class CaptionGenerator:
    """ Generates captions for the board diagram along with optional links to examples from an index. """

    _index: Dict[str, dict] = {}           # Index of example translations by rule name.
    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.
    _last_translation: tuple = ("", "")    # Translation of last root rule encountered.

    def set_rules_reversed(self, rd:Dict[StenoRule, str]) -> None:
        """ Set up the reverse rule dict. """
        self._rev_rules = rd

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Set up the index. """
        self._index = index

    def get_text(self, rule:StenoRule) -> str:
        """ Generate a plaintext caption for a rule based on its position in the current tree. """
        raw_keys = rule.keys.rtfcre
        description = rule.desc
        # If this is the root rule at the top, the title shows the keys. Just display the description by itself.
        # Save its keys and letters for later use in links.
        if RuleFlags.GENERATED in rule.flags:
            self._last_translation = raw_keys, rule.letters
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        if not rule.rulemap:
            return f"{raw_keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{raw_keys} → {rule.letters}: {description}"

    def get_link(self, rule:StenoRule) -> tuple:
        """ Look for the current rule's name in the reverse rules dict, then look for that in the index.
            If there are examples using this rule, return an HTML hyperlink to search for ones close to the root. """
        name = self._rev_rules.get(rule)
        if name is None:
            return ()
        d = self._index.get(name)
        if d is None:
            return ()
        return (name, *self._last_translation)

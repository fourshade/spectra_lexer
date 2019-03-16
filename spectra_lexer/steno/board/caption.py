from typing import Dict

from spectra_lexer.steno.rules import RuleFlags, StenoRule


class CaptionGenerator:
    """ Generates captions for the board diagram along with optional links to examples from an index. """

    _index: Dict[str, dict] = {}           # Index of example translations by rule name.
    _rev_rules: Dict[StenoRule, str] = {}  # Reverse rules dict for rule -> name translation.

    def set_rules_reversed(self, rd:Dict[StenoRule, str]) -> None:
        """ Set up the reverse rule dict. """
        self._rev_rules = rd

    def set_index(self, index:Dict[str, dict]) -> None:
        """ Set up the index. """
        self._index = index

    def get_text(self, rule:StenoRule, show_links:bool=True) -> str:
        """ Generate a caption text for a rule to go above the board diagram. """
        text = self._base_text(rule)
        if show_links and self._index:
            # If an index is loaded, check it for example text to add.
            text += self._example_text(rule)
        return text

    def _base_text(self, rule:StenoRule) -> str:
        """ Generate a plaintext caption for a rule based on its position in the current tree. """
        description = rule.desc
        # If this is a lexer-generated rule (usually the root at the top), just display the description by itself.
        if RuleFlags.GENERATED in rule.flags:
            return description
        # Base rules (i.e. leaf nodes) display their keys to the left of their descriptions.
        raw_keys = rule.keys.rtfcre
        if not rule.rulemap:
            return f"{raw_keys}: {description}"
        # Derived rules (i.e. non-leaf nodes) show the complete mapping of keys to letters in their description.
        return f"{raw_keys} → {rule.letters}: {description}"

    def _example_text(self, rule:StenoRule) -> str:
        """ Look for the current rule's name in the reverse rules dict, then look for that in the index.
            If there are examples for this rule, return a link to search them, or an empty string otherwise. """
        name = self._rev_rules.get(rule)
        if name is None:
            return ""
        d = self._index.get(name)
        if d is None:
            return ""
        return self._link_text(rule, d)

    def _link_text(self, rule:StenoRule, d:Dict[str, str]) -> str:
        """ Return hyperlink markup to search for examples. """
        return ""

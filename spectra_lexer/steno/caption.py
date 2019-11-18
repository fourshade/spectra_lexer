from typing import Hashable

from .lexer import LexerResult

# Generic marker for the rule ID reference data type (may be anything hashable).
RULE_ID = Hashable


class BoardCaptioner:
    """ Generates captions to display above the board diagram for various rules and lexer results. """

    def __init__(self) -> None:
        self._rule_captions = {}

    def add_rule(self, rule_id:RULE_ID, keys:str, letters="", desc="", has_children=False) -> None:
        """ Add a caption to be displayed on the board drawn for <rule_id>. """
        if has_children and letters:
            # Derived rules show the complete mapping of keys to letters in their caption.
            caption = f"{keys} → {letters}: {desc}"
        else:
            # Base rules display only their keys to the left of their descriptions.
            caption = f"{keys}: {desc}"
        self._rule_captions[rule_id] = caption

    def rule_caption(self, rule_id:RULE_ID) -> str:
        return self._rule_captions[rule_id]

    @staticmethod
    def result_caption(result:LexerResult) -> str:
        """ Return the caption for a lexer result. """
        if not result.unmatched_skeys():
            caption = "Found complete match."
        # The output is nowhere near reliable if some keys couldn't be matched.
        elif result.rule_ids():
            caption = "Incomplete match. Not reliable."
        else:
            caption = "No matches found."
        return caption

    @staticmethod
    def unmatched_caption(unmatched_keys:str) -> str:
        return unmatched_keys + ": unmatched keys"

from typing import Sequence


class BoardRule:
    """ Contains all information about a steno rule required for board rendering. """

    # Acceptable string values for board element flags.
    is_inversion = False
    is_linked = False
    is_unmatched = False
    is_rare = False
    is_fingerspelling = False
    is_brief = False

    def __init__(self, skeys:str, letters:str, alt_text:str, children:Sequence['BoardRule']) -> None:
        self.skeys = skeys         # String of steno s-keys that make up the rule.
        self.letters = letters     # English text of the rule, if any.
        self.alt_text = alt_text   # Alternate text to display when not in letters mode (or if there are no letters).
        self.children = children   # Sequence of child rules *in order*.

from __future__ import annotations

from spectra_lexer.keys import StenoKeys, is_separator
from spectra_lexer.rules import StenoRule
from spectra_lexer.struct import Node

# Acceptable rule flags that indicate special behavior for output formatting.
OUTPUT_FLAGS = {"INV": "Inversion of steno order. Should appear different on format drawing."}


# Default limit on number of recursion steps to allow for rules that contain other rules.
RECURSION_LIMIT = 10


class OutputNode(Node):
    """
    Class representing a node in a tree structure containing the information required to display a complete graph
    of an analysis from the lexer. Where used as a dict key, hashing is by identity only.
    """

    attach_start: int             # Index of character where this node attaches to its parent.
    attach_length: int            # Length of the attachment (may be different than its letters due to substitutions).
    text: str                     # Display text of the node (either letters or RTFCRE keys).
    raw_keys: StenoKeys           # Raw/lexer-formatted keys to be drawn on the board diagram.
    description: str              # Rule description for the board diagram.
    is_separator: bool = False    # Directive for drawing the stroke separator rule.
    is_inversion: bool = False    # Directive for drawing a rule that uses inversion of steno order.

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
                maxdepth = 0 only displays the root node.
                maxdepth = 1 displays the root node and all of the rules that make it up.
                maxdepth = 2 also displays the rules that make up each of those, and so on. """
        super().__init__()
        keys, letters, flags, desc, rulemap = rule
        self.attach_start = start
        self.attach_length = length
        self.raw_keys = keys
        self.is_separator = is_separator(keys)
        self.is_inversion = "INV" in flags
        self.children = []
        if maxdepth:
            self.add_children([OutputNode(i.rule, i.start, i.length, maxdepth - 1) for i in rulemap])
        formatted_keys = keys.to_rtfcre()
        if not rulemap or not maxdepth:
            # Base rules (i.e. leaf nodes) and rules at the max depth display their keys instead of their letters.
            # Since the descriptions of these are rather short, they also include the keys to the left.
            self.text = formatted_keys
            self.description = "{}: {}".format(formatted_keys, desc)
        else:
            # Derived rules (i.e. non-leaf nodes) above the max depth show their letters.
            # They also include the complete mapping of keys to letters in their description.
            self.text = letters
            self.description = "{} → {}: {}".format(formatted_keys, letters, desc)

    def __str__(self):
        return "{} → {}".format(self.text, self.children)


class OutputTree(OutputNode):
    """ Special subclass for the root node of an output tree, which contains everything else. """

    def __init__(self, rule:StenoRule, maxdepth:int=RECURSION_LIMIT):
        """ The root node has no parent, its "attach interval" is arbitrarily
            defined as starting at 0 and being the length of its letters. """
        super().__init__(rule, 0, len(rule.letters), min(maxdepth, RECURSION_LIMIT))
        # The root node always shows letters and does not include anything extra in its description.
        self.text = rule.letters
        self.description = rule.desc

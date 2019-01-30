from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import OutputFlags, StenoRule
from spectra_lexer.struct import Node

# Default limit on number of recursion steps to allow for rules that contain other rules.
_RECURSION_LIMIT = 10
# Text symbols at the start that may not be covered by connectors, such as side split hyphens.
_UNCOVERED_PREFIXES = {"-"}
# Set of all flags defined as display-altering. Currently, only one at a time can be active.
OUTPUT_FLAG_SET = set(vars(OutputFlags).values())


class OutputNode(Node):
    """
    Class representing a node in a tree structure containing the information required to display a complete graph
    of an analysis from the lexer. Where used as a dict key, hashing is by identity only.
    """

    attach_start: int             # Index of character where this node attaches to its parent.
    attach_length: int            # Length of the attachment (may be different than its letters due to substitutions).
    bottom_start: int = 0         # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.
    bottom_length: int            # Length of the bottom attach point. Is the length of the text unless start is !=0.
    text: str                     # Display text of the node (either letters or RTFCRE keys).
    raw_keys: StenoKeys           # Raw/lexer-formatted keys to be drawn on the board diagram.
    description: str              # Rule description for the board diagram.
    appearance: str = None        # Special rule display flag. Only one is allowed; is used as a dict key.

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
                maxdepth = 0 only displays the root node.
                maxdepth = 1 displays the root node and all of the rules that make it up.
                maxdepth = 2 also displays the rules that make up each of those, and so on. """
        keys, letters, flags, desc, rulemap = rule
        super().__init__([OutputNode(i.rule, i.start, i.length, maxdepth - 1) for i in rulemap] if maxdepth else ())
        self.attach_start = start
        self.attach_length = length
        self.raw_keys = keys
        # If there are any flags at all, look for an output flag specifically. There should only be one (if any).
        if flags:
            for f in flags.intersection(OUTPUT_FLAG_SET):
                self.appearance = f
        formatted_keys = keys.to_rtfcre()
        if not rulemap or not maxdepth:
            # Base rules (i.e. leaf nodes) and rules at the max depth display their keys instead of their letters.
            # Since the descriptions of these are rather short, they also include the keys to the left.
            text = self.text = formatted_keys
            self.description = "{}: {}".format(formatted_keys, desc)
            # The bottom attach start is shifted one to the right if the keys start with a hyphen.
            bstart = self.bottom_start = text[0] in _UNCOVERED_PREFIXES
            self.bottom_length = len(text) - bstart
        else:
            # Derived rules (i.e. non-leaf nodes) above the max depth show their letters.
            # They also include the complete mapping of keys to letters in their description.
            text = self.text = letters
            self.description = "{} → {}: {}".format(formatted_keys, letters, desc)
            self.bottom_length = len(text)

    def __str__(self):
        return "{} → {}".format(self.text, self.children)


class OutputTree(OutputNode):
    """ Special subclass for the root node of an output tree, which contains everything else. """

    def __init__(self, rule:StenoRule, maxdepth:int=_RECURSION_LIMIT):
        """ The root node has no parent, its "attach interval" is arbitrarily
            defined as starting at 0 and being the length of its letters. """
        super().__init__(rule, 0, len(rule.letters), min(maxdepth, _RECURSION_LIMIT))
        # The root node always shows letters and does not include anything extra in its description.
        self.text = rule.letters
        self.description = rule.desc

from typing import List, Tuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import StenoRule

# Acceptable rule flags that indicate special behavior for output formatting.
OUTPUT_FLAGS = {"INV": "Inversion of steno order. Should appear different on format drawing.",
                "KEY": "Indicates a rule where a key does not contribute to the letters of the word."}
OUTPUT_FLAG_SET = set(OUTPUT_FLAGS.keys())


class OutputNode:
    """
    Class representing a node in a tree structure (each node contains data along with a list of child nodes).
    The complete tree contains the information required to display a graph of an analysis from the lexer.

    Note that nodes do not have entirely immutable contents. Since they must be used as dict keys, hashing
    is by identity only (the default for class `object`). This is sufficient for any purposes we need.
    """

    attach_start: int             # Index of character where this node attaches to its parent.
    attach_length: int            # Length of the attachment (may be different than its letters due to substitutions).
    text: str                     # Display text of the node (either letters or str-keys).
    raw_keys: StenoKeys           # Raw/lexer-formatted keys to be drawn on the board diagram.
    description: str              # Rule description for the board diagram.
    is_separator: bool = False    # Directive for drawing the stroke separator rule.
    is_inversion: bool = False    # Directive for drawing a rule that uses inversion of steno order.
    is_key_rule: bool = False     # Directive for drawing key rules. These don't map to any letters at all.
    parent: __qualname__          # Direct parent of the node. If None, it is the root node.
    children: List[__qualname__]  # Direct children of the node. If empty, it is considered a "base rule".

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int, parent:__qualname__=None):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
                maxdepth = 0 only displays the root node.
                maxdepth = 1 displays the root node and all of the rules that make it up.
                maxdepth = 2 also displays the rules that make up each of those, and so on. """
        keys, letters, flags, desc, rulemap = rule
        self.attach_start = start
        self.attach_length = length
        self.raw_keys = keys
        self.is_separator = rule.is_separator()
        self.is_inversion = "INV" in flags
        self.is_key_rule = "KEY" in flags
        self.parent = parent
        self.children = [OutputNode(i.rule, i.start, i.length, maxdepth - 1, self) for i in rulemap] if maxdepth else []
        formatted_keys = keys.inv_parse()
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

    def get_ancestors(self) -> List[__qualname__]:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return [self] + self.parent.get_ancestors()

    def get_descendents(self) -> List[__qualname__]:
        """ Get a list of all descendents of this node (starting with itself) down to the base. """
        return sum([c.get_descendents() for c in self.children], [self])

    def get_board_info(self) -> Tuple[StenoKeys, str]:
        """ Get the basic info necessary to display the rule on a steno board diagram. """
        return self.raw_keys, self.description

    def __str__(self):
        return "{} → {}".format(self.text, self.children)

    __repr__ = __str__


class OutputTree(OutputNode):
    """ Special subclass for the root node of an output tree, which contains everything else. """

    def __init__(self, rule:StenoRule, maxdepth:int):
        """ The root node has no parent, its "attach interval" is arbitrarily
            defined as starting at 0 and being the length of its letters. """
        super().__init__(rule, 0, len(rule.letters), maxdepth, None)
        # The root node always shows letters and does not include anything extra in its description.
        self.text = rule.letters
        self.description = rule.desc

    def get_ancestors(self) -> List[__qualname__]:
        """ The root node has no ancestors, but since ancestry is inclusive, return only itself. """
        return [self]

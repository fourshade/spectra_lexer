from typing import List

from spectra_lexer import SpectraComponent
from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import StenoRule

# Default limit on number of recursion steps to allow for rules that contain other rules.
RECURSION_LIMIT = 10

# Acceptable rule flags that indicate special behavior for the output formatter.
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
        """ Create a new node from a rule and recursively populate child nodes with rules from the map. """
        keys, letters, flags, desc, rulemap = rule
        self.attach_start = start
        self.attach_length = length
        self.raw_keys = keys
        self.is_separator = rule.is_separator()
        self.is_inversion = "INV" in flags
        self.is_key_rule = "KEY" in flags
        self.parent = parent
        self.children = [OutputNode(i.rule, i.start, i.length, maxdepth - 1, self) for i in rulemap] if maxdepth else []
        if parent is None:
            # The root node always shows letters and does not include anything extra in its description.
            self.text = letters
            self.description = desc
        else:
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
        nodes = []
        while self is not None:
            nodes.append(self)
            self = self.parent
        return nodes

    def get_descendents(self) -> List[__qualname__]:
        """ Get a list of all descendents of this node (starting with itself) down to the base. """
        stack = self.children[:]
        nodes = [self]
        while stack:
            node = stack.pop()
            nodes.append(node)
            stack.extend(node.children)
        return nodes

    def __str__(self):
        return "{} → {}".format(self.text, self.children)

    __repr__ = __str__


class OutputFormatter(SpectraComponent):
    """ Base output class for creating and formatting a finished rule breakdown of steno translations.
        Only meant to be subclassed by more specific classes based on the output type (graphics, text, etc.) """

    _max_depth: int  # Maximum recursion depth to draw in output tree.
                     # max_depth = 0 only displays the root node.
                     # max_depth = 1 displays the root node and all of the rules that make it up.
                     # max_depth = 2 also displays the rules that make up each of those, and so on.

    def __init__(self, maxdepth:int=RECURSION_LIMIT):
        self._max_depth = min(maxdepth, RECURSION_LIMIT)

    def make_tree(self, rule:StenoRule) -> OutputNode:
        """ Make a display tree from the given rule and return the root node (which contains everything else).
            The root node has no map, so set its start to 0 and length to the length of the word. """
        return OutputNode(rule, 0, len(rule.letters), self._max_depth, None)

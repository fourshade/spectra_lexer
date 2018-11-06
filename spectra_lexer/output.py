from typing import List

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules.rules import RuleMap, StenoRule

# Default limit on number of recursion steps to allow for rules that contain other rules.
RECURSION_LIMIT = 10

# Acceptable rule flags that indicate special behavior for the output formatter.
OUTPUT_FLAGS = {"INV": "Inversion of steno order. Should appear different on format drawing.",
                "KEY": "Indicates a rule where a key does not contribute to the letters of the word."}
OUTPUT_FLAG_SET = set(OUTPUT_FLAGS.keys())


class OutputNode(object):
    """
    Class representing a node in a tree structure (each node contains data along with a list of child nodes).
    The complete tree contains the information required to display a graph of an analysis from the lexer.

    Note that nodes do not have entirely immutable contents. Since they must be used as dict keys, hashing
    is by identity only (the default for class `object`). This is sufficient for any purposes we need.
    """

    attach_start: int             # Index of character where this node attaches to its parent.
    attach_length: int            # Length of the attachment (may be different than its letters due to substitutions).
    text: str                     # Display text of the node (either letters or str-keys).
    raw_keys: StenoKeys           # Raw format keys used to display on the board diagram.
    description: str              # Rule description for the board diagram.
    is_separator: bool = False    # Directive for drawing the stroke separator rule.
    is_inversion: bool = False    # Directive for drawing a rule that uses inversion.
    is_key_rule: bool = False     # Directive for drawing key rules. These don't map to any letters at all.
    parent: __qualname__          # Direct parent of the node. If None, it is the root node.
    children: List[__qualname__]  # Direct children of the node. If empty, it is considered a "base rule".

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int, parent:__qualname__=None):
        """
        Create a new node from a rule and recursively populate child nodes with rules from the map.
        max_depth = 0 only displays the root node.
        max_depth = 1 displays the root node and all of the rules that make it up.
        max_depth = 2 also displays the rules that make up each of those, and so on.
        """
        name, keys, letters, flags, desc, rulemap = rule
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


class LexerOutput(object):
    """ Base class for analyzing and formatting the text display of a rule tree.
        It is one of the only classes that should be exposed to the GUI and console script. """

    keys: StenoKeys   # The unformatted key set used to set up the board diagram.
    desc: str         # The description of the lexer output as shown when a stroke is selected.
    title: str        # The text displayed in the title bar above the text.
    _rule: StenoRule  # The root rule used to construct the output tree.

    def __init__(self, keys: StenoKeys, letters: str, rulemap: RuleMap):
        self.keys = keys
        if rulemap:
            matchable_letters = sum(c is not ' ' for c in letters)
            if matchable_letters:
                percent_match = rulemap.letters_matched() * 100 / matchable_letters
            else:
                percent_match = 0
            self.desc = "Found {:d}% match.".format(int(percent_match))
        else:
            self.desc = "No matches found."
        # The title of the analysis 'strokes -> word'
        self.title = "{} → {}".format(keys.inv_parse(), letters)
        self._rule = StenoRule(str(id(self)), keys, letters, (), self.desc, rulemap)

    def make_tree(self, maxdepth: int = RECURSION_LIMIT) -> OutputNode:
        """ Make an output tree from the saved collection of parameters.
            The root node has no map, so set its start to 0 and length to the length of the word. """
        return OutputNode(self._rule, 0, len(self._rule.letters), min(maxdepth, RECURSION_LIMIT), None)

""" Module for a generic graph node of any type. Contains enough information for display-agnostic operations. """

from typing import Sequence

from spectra_lexer.rules import RuleFlags, StenoRule
from spectra_lexer.utils import recurse, traverse


# Default limit on number of recursion steps to allow for rules that contain other rules.
_RECURSION_LIMIT = 10


class GraphNode:
    """ Class representing a node in a tree structure of steno rules with linear indexing.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child sequence may be mutable, hashing is by identity only. """

    # Acceptable rule flags that indicate special behavior for output graph formatting.
    FLAG_SEPARATOR = RuleFlags.SEPARATOR  # Stroke separator. Unconnected; does not appear as direct text.
    FLAG_UNMATCHED = RuleFlags.UNMATCHED  # Incomplete lexer result. Unmatched keys connect to question marks.
    FLAG_INVERSION = RuleFlags.INVERSION  # Inversion of steno order. Appears different on format drawing.
    # Set of all flags defined as display-altering. Currently, only one at a time can be active.
    OUTPUT_FLAG_SET = {FLAG_SEPARATOR, FLAG_UNMATCHED, FLAG_INVERSION}

    rule: StenoRule          # Original rule, kept only as a means of unique identification and for compatibility.
    attach_start: int = 0    # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int       # Length of the attachment (may be different than its letters due to substitutions).
    flags: set               # Specific output modifier flags.
    parent = None            # Direct parent of the node. If None, it is the root node (or unconnected).
    children: Sequence = ()  # Direct children of the node. If empty, it is considered a leaf node.

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int=_RECURSION_LIMIT):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
            maxdepth = 0 only displays the root node.
            maxdepth = 1 displays the root node and all of the rules that make it up.
            maxdepth = 2 also displays the rules that make up each of those, and so on. """
        keys, letters, flags, desc, rulemap = rule
        self.attach_start = start
        self.attach_length = length
        self.rule = rule
        if rulemap and maxdepth:
            nodes = [self.__class__(i.rule, i.start, i.length, maxdepth - 1) for i in rulemap]
            for n in nodes:
                n.parent = self
            self.children = nodes
        # Save the output flags (if any).
        self.flags = flags & self.OUTPUT_FLAG_SET

    def get_ancestors(self) -> list:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return list(traverse(self, next_attr="parent"))

    def get_descendents(self) -> list:
        """ Get a list of all descendents of this node (starting with itself) searching depth-first. """
        return list(recurse(self, iter_attr="children"))

    def __str__(self):
        return "{} → {}".format(self.rule, self.children)

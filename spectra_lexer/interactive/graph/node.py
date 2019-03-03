""" Module for a generic graph node of any type. Contains enough information for display-agnostic operations. """

from typing import Sequence

from spectra_lexer.rules import RuleFlags, StenoRule
from spectra_lexer.utils import recurse, traverse, with_sets


@with_sets
class GraphNodeAppearance:
    """ Flags that indicate special behavior for drawing a node on a graph. """
    SEPARATOR = RuleFlags.SEPARATOR  # Stroke separator. Unconnected; does not appear as direct text.
    UNMATCHED = RuleFlags.UNMATCHED  # Incomplete lexer result. Unmatched keys connect to question marks.
    INVERSION = RuleFlags.INVERSION  # Inversion of steno order. Connections appear different.
    ROOT = "ROOT"                    # Root node; has no parent.
    BRANCH = "BRANCH"                # Branch node; has one or more children.
    LEAF = "LEAF"                    # Leaf node; has no children.


class GraphNode:
    """ Class representing a node in a tree structure of steno rules with linear indexing.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child sequence may be mutable, hashing is by identity only. """

    RECURSION_LIMIT = 10     # Default limit on number of recursion steps to allow for rules that contain other rules.

    rule: StenoRule          # Original rule, kept only as a means of unique identification and for compatibility.
    attach_start: int        # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int       # Length of the attachment (may be different than its letters due to substitutions).
    parent = None            # Direct parent of the node. If None, it is the root node (or unconnected).
    children: Sequence = ()  # Direct children of the node. If empty, it is considered a leaf node.
    appearance: str = GraphNodeAppearance.LEAF  # Special appearance flag for formatting. Default is a base (leaf) node.

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int=RECURSION_LIMIT):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
            maxdepth = 0 only displays the root node.
            maxdepth = 1 displays the root node and all of the rules that make it up.
            maxdepth = 2 also displays the rules that make up each of those, and so on. """
        keys, letters, flags, desc, rulemap = self.rule = rule
        self.attach_start = start
        self.attach_length = length
        if rulemap and maxdepth:
            nodes = [self.__class__(i.rule, i.start, i.length, maxdepth - 1) for i in rulemap]
            for n in nodes:
                n.parent = self
            self.children = nodes
            self.appearance = GraphNodeAppearance.BRANCH
        # If there are legal appearance flags on the rule, use the first one to override the tree-based appearance flag.
        if flags:
            appearance_flags = flags & GraphNodeAppearance.values
            if appearance_flags:
                self.appearance = next(iter(appearance_flags))

    def get_ancestors(self) -> list:
        """ Get a list of all ancestors of this node (starting with itself) up to the root. """
        return list(traverse(self, next_attr="parent"))

    def get_descendents(self) -> list:
        """ Get a list of all descendents of this node (starting with itself) searching depth-first. """
        return list(recurse(self, iter_attr="children"))

    def __str__(self):
        return f"{self.rule} → {self.children}"

    @classmethod
    def for_display(cls, rule:StenoRule, recursive:bool=False):
        """ Special method to generate a full output tree starting with the given rule as root.
            The root node has no parent; its "attach interval" is arbitrarily defined as starting
            at 0 and being the length of its letters, and its appearance flag overrides all others. """
        maxdepth = 1 if not recursive else cls.RECURSION_LIMIT
        self = cls(rule, 0, len(rule.letters), maxdepth)
        self.appearance = GraphNodeAppearance.ROOT
        return self

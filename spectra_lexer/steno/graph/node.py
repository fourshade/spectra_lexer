""" Module for graph nodes. Contains enough information for text operations. """

from typing import Sequence

from spectra_lexer.steno.keys import KEY_SEP, KEY_SPLIT
from spectra_lexer.steno.rules import RuleFlags, StenoRule
from spectra_lexer.utils import recurse, traverse, with_sets


@with_sets
class GraphNodeAppearance:
    """ Flags that indicate special behavior for drawing a node on a graph. """
    UNMATCHED = RuleFlags.UNMATCHED  # Incomplete lexer result. Unmatched keys connect to question marks.
    INVERSION = RuleFlags.INVERSION  # Inversion of steno order. Connections appear different.
    SEPARATOR = "SEP"                # Stroke separator. Unconnected; does not appear as direct text.
    ROOT = "ROOT"                    # Root node; has no parent.
    BRANCH = "BRANCH"                # Branch node; has one or more children.
    LEAF = "LEAF"                    # Leaf node; has no children.


class GraphNode:
    """ Class representing a node in a tree structure of steno rules with linear indexing.
        Each node may have zero or more children and zero or one parent of the same type.
        Since the child sequence may be mutable, hashing is by identity only. """

    RECURSION_LIMIT = 10     # Default limit on number of recursion steps to allow for rules that contain other rules.

    rule: StenoRule          # Original rule, kept only as a means of unique identification and for compatibility.
    text: str                # Display text of the node (either letters or RTFCRE keys).
    attach_start: int        # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int       # Length of the attachment (may be different than its letters due to substitutions).
    bottom_start: int = 0    # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.
    bottom_length: int       # Length of the bottom attach point. Is the length of the text unless start is !=0.
    parent = None            # Direct parent of the node. If None, it is the root node (or unconnected).
    children: Sequence = ()  # Direct children of the node. If empty, it is considered a leaf node.
    appearance: str = GraphNodeAppearance.LEAF  # Special appearance flag for formatting. Default is a base (leaf) node.

    def __init__(self, rule:StenoRule, start:int, length:int, maxdepth:int=RECURSION_LIMIT):
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to.
            maxdepth = 0 only displays the root node.
            maxdepth = 1 displays the root node and all of the rules that make it up.
            maxdepth = 2 also displays the rules that make up each of those, and so on. """
        keys, letters, flags, _, rulemap = self.rule = rule
        self.attach_start = start
        self.attach_length = length
        if rulemap and maxdepth:
            # Derived rules (i.e. non-leaf nodes) show their letters.
            self.text = letters
            self.bottom_length = len(letters)
            nodes = [self.__class__(i.rule, i.start, i.length, maxdepth - 1) for i in rulemap]
            for n in nodes:
                n.parent = self
            self.children = nodes
            self.appearance = GraphNodeAppearance.BRANCH
        else:
            # Base rules (i.e. leaf nodes) show their keys instead of their letters.
            self.text = formatted_keys = keys.rtfcre
            # The bottom attach start is shifted one to the right if the keys start with a hyphen.
            bstart = self.bottom_start = (formatted_keys[:1] == KEY_SPLIT)
            self.bottom_length = len(formatted_keys) - bstart
            # Single separators have their own appearance.
            if formatted_keys == KEY_SEP:
                self.appearance = GraphNodeAppearance.SEPARATOR
        # If there are legal appearance flags on the rule, use the first one to override the tree-based appearance flag.
        if flags:
            for f in (flags & GraphNodeAppearance.values):
                self.appearance = f
                break

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
            at 0 and being the length of its letters, and its appearance flag overrides all others.
            The root node's text always shows letters no matter what. """
        maxdepth = 1 if not recursive else cls.RECURSION_LIMIT
        self = cls(rule, 0, len(rule.letters), maxdepth)
        self.text = rule.letters
        self.appearance = GraphNodeAppearance.ROOT
        return self

""" Module for graph nodes. Contains enough information for text operations. """

from functools import partialmethod
from typing import Sequence

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

    rule: StenoRule          # Original rule, kept only as a means of unique identification and for compatibility.
    attach_start: int        # Index of the letter in the parent node where this node begins its attachment.
    attach_length: int       # Length of the attachment (may be different than its letters due to substitutions).
    parent: object           # Direct parent of the node. If None, it is the root node (or unconnected).
    text: str                # Display text of the node (either letters or keys).
    bottom_start: int = 0    # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.
    bottom_length: int       # Length of the bottom attach point. Is the length of the text unless start is !=0.
    children: Sequence = ()  # Direct children of the node. If empty, it is considered a leaf node.
    appearance: str          # Special appearance flag for formatting.

    # Get all ancestors of this node (starting with itself) up to the root.
    ancestors = partialmethod(traverse, "parent")
    # Get all descendents of this node (starting with itself) searching depth-first.
    descendents = partialmethod(recurse, "children")

    def __str__(self):
        return f"{self.rule} → {self.children}"


class NodeOrganizer:

    RECURSION_LIMIT: int = 10  # Limit on number of recursion steps to allow for rules that contain other rules.

    _key_sep: str    # Steno key used as stroke separator.
    _key_split: str  # Steno key used to split sides in RTFCRE.

    def __init__(self, key_sep:str, key_split:str):
        self._key_sep = key_sep
        self._key_split = key_split

    def make_tree(self, rule:StenoRule, recursive:bool=True) -> GraphNode:
        """ Method to generate a full output tree starting with the given rule as root.
            The root node has no parent; its "attach interval" is arbitrarily defined as starting
            at 0 and being the length of its letters, and its appearance flag overrides all others.
            The root node's text always shows letters no matter what. """
        root = self.make_node(rule, 0, len(rule.letters), None, self.RECURSION_LIMIT if recursive else 1)
        root.text = rule.letters
        root.appearance = GraphNodeAppearance.ROOT
        return root

    def make_node(self, rule:StenoRule, start:int, length:int, parent:object, maxdepth:int) -> GraphNode:
        """ Create a new node from a rule and recursively populate child nodes with rules from the map.
            maxdepth is the maximum recursion depth to draw nodes out to. """
        node = GraphNode()
        node.rule = rule
        node.attach_start = start
        node.attach_length = length
        node.parent = parent
        if rule.rulemap and maxdepth:
            # Derived rules (i.e. non-leaf nodes) show their letters.
            node.text = letters = rule.letters
            node.bottom_length = len(letters)
            node.appearance = GraphNodeAppearance.BRANCH
            node.children = [self.make_node(i.rule, i.start, i.length, node, maxdepth - 1) for i in rule.rulemap]
        else:
            # Base rules (i.e. leaf nodes) show their keys instead of their letters.
            node.text = keys = rule.keys
            node.bottom_length = key_length = len(keys)
            node.appearance = GraphNodeAppearance.LEAF
            if key_length > 1:
                # The bottom attach start is shifted one to the right if the keys start with the split key.
                if keys[0] == self._key_split:
                    node.bottom_start = 1
                    node.bottom_length -= 1
            elif keys == self._key_sep:
                # The singular stroke separator has a special appearance (or is removed, depending on layout).
                node.appearance = GraphNodeAppearance.SEPARATOR
        # If there are legal appearance flags on the rule, use the first one to override the tree-based appearance flag.
        if rule.flags:
            for f in (rule.flags & GraphNodeAppearance.values):
                node.appearance = f
                break
        return node

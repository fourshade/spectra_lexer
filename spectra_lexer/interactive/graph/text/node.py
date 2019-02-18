from spectra_lexer.interactive.graph.node import GraphNode, GraphFlags
from spectra_lexer.rules import StenoRule

# Text symbols at the start of text that may not be covered by connectors, such as side split hyphens.
_UNCOVERED_PREFIXES = {"-"}


class TextFlags(GraphFlags):
    """ Additional flags that indicate special behavior for text graph formatting. """
    ROOT = "ROOT"      # Root node; has no parent.
    BRANCH = "BRANCH"  # Branch node; has one or more children.
    LEAF = "LEAF"      # Leaf node; has no children.


class TextNode(GraphNode):
    """ Graph node containing extra information to display a complete text graph of an analysis from the lexer. """

    bottom_start: int = 0  # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.
    bottom_length: int     # Length of the bottom attach point. Is the length of the text unless start is !=0.
    text: str              # Display text of the node (either letters or RTFCRE keys).
    appearance: str = TextFlags.LEAF  # Special appearance flag for formatting. Default is a base (leaf) node.

    def __init__(self, rule:StenoRule, *args):
        """ Add node characteristics that are helpful for text graphing. """
        super().__init__(rule, *args)
        formatted_keys = rule.keys.rtfcre
        if not self.children:
            # Base rules (i.e. leaf nodes) display their keys instead of their letters.
            self.text = formatted_keys
            # The bottom attach start is shifted one to the right if the keys start with a hyphen.
            bstart = self.bottom_start = formatted_keys[0] in _UNCOVERED_PREFIXES
            self.bottom_length = len(formatted_keys) - bstart
        else:
            # Derived rules (i.e. non-leaf nodes) show their letters.
            self.text = rule.letters
            self.bottom_length = len(rule.letters)
            self.appearance = TextFlags.BRANCH
        # If we have one or more output flags, use the first one to define appearance.
        if self.flags:
            self.appearance = next(iter(self.flags))

    @classmethod
    def for_display(cls, rule:StenoRule, recursive:bool=False, *args):
        """ Special method to generate a full output tree starting with the given rule as root.
            The root node has no parent; its "attach interval" is arbitrarily defined as starting
            at 0 and being the length of its letters. Its text always shows letters no matter what. """
        maxdepth = 1 if not recursive else cls.RECURSION_LIMIT
        self = cls(rule, 0, len(rule.letters), maxdepth, *args)
        self.text = rule.letters
        self.appearance = TextFlags.ROOT
        return self

from spectra_lexer.graph.node import GraphNode
from spectra_lexer.rules import StenoRule

# Text symbols at the start of text that may not be covered by connectors, such as side split hyphens.
_UNCOVERED_PREFIXES = {"-"}


class TextNode(GraphNode):
    """ Graph node containing extra information to display a complete text graph of an analysis from the lexer. """

    bottom_start: int = 0  # Start of the bottom attach point. Is only non-zero if there is an uncovered prefix.
    bottom_length: int     # Length of the bottom attach point. Is the length of the text unless start is !=0.
    text: str              # Display text of the node (either letters or RTFCRE keys).

    def __init__(self, rule:StenoRule, *args):
        """ Add node characteristics that are helpful for text graphing. """
        super().__init__(rule, *args)
        formatted_keys = rule.keys.to_rtfcre()
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

    @classmethod
    def for_display(cls, rule:StenoRule):
        """ Special method to generate a full output tree starting with the given rule as root.
            The root node has no parent; its "attach interval" is arbitrarily defined as starting
            at 0 and being the length of its letters. Its text always shows letters no matter what. """
        self = cls(rule, 0, len(rule.letters))
        self.text = rule.letters
        return self

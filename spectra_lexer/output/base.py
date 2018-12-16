from spectra_lexer import on, SpectraComponent
from spectra_lexer.output.node import OutputTree
from spectra_lexer.rules import StenoRule

# Default limit on number of recursion steps to allow for rules that contain other rules.
RECURSION_LIMIT = 10


class OutputFormatter(SpectraComponent):
    """ Base output class for creating and formatting a finished rule breakdown of steno translations.
        Output is meant to be used by more specific classes (graphics, text, etc.) """

    @on("new_lexer_result")
    def make_tree(self, rule:StenoRule, maxdepth:int=RECURSION_LIMIT) -> OutputTree:
        """ Make a display tree from the given rule and save it. Must be handled further by subclasses. """
        tree = OutputTree(rule, maxdepth)
        self.engine_call("new_output_tree", tree)
        return tree

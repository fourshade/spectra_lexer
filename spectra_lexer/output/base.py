from spectra_lexer import pipe, Composite
from spectra_lexer.output.board import BoardDiagram
from spectra_lexer.output.node import OutputTree
from spectra_lexer.output.text import TextGraph
from spectra_lexer.rules import StenoRule


class DisplayEngine(Composite):
    """ Main component of the display package. Contains the board diagram generator and the text graph generator. """

    ROLE = "output"
    COMPONENTS = [BoardDiagram, TextGraph]

    @pipe("new_lexer_result", "new_output_tree")
    def make_tree(self, rule:StenoRule) -> OutputTree:
        """ Generate a display tree for a steno rule and send the title. """
        tree = OutputTree(rule)
        self.engine_call("new_output_title", str(rule))
        return tree

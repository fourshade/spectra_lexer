""" Module for generating a compressed text graph. Nodes are drawn in a rectangular shape as closely as possible. """

from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.graph import TextGraph, TextGraphLine, TextGraphBlock


class CompressedTextGraph(TextGraph):
    """
    Specialized structure for a compressed plaintext breakdown of steno translations.
    This layout is much more compact than cascaded, but can look crowded and confusing.
    Nodes require much more clever placement to avoid ambiguities and wasted space.
    """

    def draw(self, node:OutputNode) -> None:
        """ Draw the root node from scratch, starting from the left end.
            Shallow copy the entire root block to the main graph to finish. """
        self[:] = self._draw(node)

    def _draw(self, node:OutputNode, offset:int=0) -> TextGraphBlock:
        """ Add the root node from scratch, starting from the left end with a template of spaces
            as long as the text. """
        template = TextGraphLine.filler(len(node.text))
        block = TextGraphBlock()
        # n_text = TextGraphLine(template)
        # n_text.write(node.text, node, offset)
        # self.append(n_text)
        # block.extend([template for x in range(10)])
        # self.extend([template for x in range(10)])
        # self.write_block(block, 5, 5)
        return block

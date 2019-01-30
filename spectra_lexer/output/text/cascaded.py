""" Module for generating a cascaded text graph. Nodes are drawn in an upper-triangular grid configuration. """

from itertools import starmap

from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.graph import TextGraph, TextGraphLine


class CascadedTextGraph(TextGraph):
    """
    Specialized structure for a cascaded plaintext breakdown of steno translations.
    Nodes are drawn in descending order like a waterfall going left-to-right.
    Recursive construction from the bottom up means everything fits naturally with no overlap.
    Performance is very good due to heavy re-use and copying of pre-drawn template lines.
    Window space economy is poor (the triangle shape means half the space is wasted off the top).
    Aspect ratio is highly vertical, requiring an awkwardly shaped display window to accommodate.
    """

    def draw(self, node:OutputNode, offset:int=0, template:TextGraphLine=None) -> None:
        """ Add the body of a node, which includes its text line, connectors, and any descending children. """
        if template is None:
            template = TextGraphLine.filler(len(node.text))
        # Add the node text itself. If the last child is off the right end, add extensions to connect it.
        self._copy_mutate_add(node, offset, template, TextGraphLine.add_node_string)
        # If there are no children for this node, there is nothing else to do.
        children = node.children
        if children:
            # Gather all node and offset data from children, not counting separators.
            data = [(node, offset + node.attach_start) for node in children if not node.is_separator]
            # Add all of the top containers at once.
            top = TextGraphLine(template)
            list(starmap(top.add_top_container, data))
            self.append(top)
            # Prepare the cascading connectors by building up starting from the right.
            first = TextGraphLine(template)
            lines = [_connector_add(template, *d) for d in reversed(data[1:])]
            lines.reverse()
            lines.append(first)
            # Add all normally-connected children (i.e. not separators) in order building down.
            for i, ((node, offset), line) in enumerate(zip(data, lines)):
                # if node.is_separator:
                #     self[-1].add_separators()
                #     continue
                # Add the bottom container and start on the node body (and its children, if any) recursively.
                if i > 0 or node.bottom_length > 1:
                    # If the first child attaches with a single character, don't draw its bottom container line.
                    self._copy_mutate_add(node, offset, line, TextGraphLine.add_bottom_container)
                self.draw(node, offset, line)

    def _copy_mutate_add(self, node:OutputNode, offset:int, line:TextGraphLine, meth:callable):
        line = TextGraphLine(line)
        meth(line, node, offset)
        self.append(line)


def _connector_add(line, node, offset):
    line.add_connector(node, offset)
    return TextGraphLine(line)

# If a base node doesn't overlap the last line drawn, write the node text there instead of a new line.

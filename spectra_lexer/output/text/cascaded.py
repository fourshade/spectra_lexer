""" Module for generating a cascaded text graph. Nodes are drawn in an upper-triangular grid configuration. """

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

    last_bounds = 9999

    def draw(self, node:OutputNode, offset:int=0, template:TextGraphLine=None) -> None:
        """ Add the body of a node, which includes its text line, connectors, and any descending children. """
        if template is None:
            template = TextGraphLine.filler(len(node.text))
        # Add the node text itself. If the last child is off the right end, add extensions to connect it.
        n_text = TextGraphLine(template)
        n_text.add_node_string(node, offset)
        self.append(n_text)
        # If there are children, prepare the top row and cascading connectors by building up starting from the right.
        if node.children:
            top = TextGraphLine(template)
            lines = []
            for child in reversed(node.children):
                # Don't draw connectors for separators, but mark the previous child so it can draw the slashes.
                if child.is_separator and lines:
                    lines[-1][-1] = True
                    continue
                attach = offset + child.attach_start
                lines.append([child, attach, template, False])
                template = TextGraphLine(template)
                top.add_top_container(child, attach)
                template.add_connector(child, attach)
            self.append(top)
            # Add all normally-connected children (i.e. not separators) in order building down.
            for (node, offset, template, after_sep) in lines[-1::-1]:
                # If the first child attaches with a single character, don't draw its bottom container line.
                if node.attach_start > 0 or node.bottom_length > 1:
                    # If a base node doesn't overlap the last line drawn, start drawing there instead of a new line.
                    btemplate = TextGraphLine(template) if offset < self.last_bounds or after_sep else self.pop()
                    # If this child follows a separator, the bottom container is a good place to divide the graph.
                    if after_sep:
                        btemplate.add_separators()
                    btemplate.add_bottom_container(node, offset)
                    self.append(btemplate)
                    self.last_bounds = offset + node.bottom_length
                # Start on the node body (and its children, if any) recursively.
                self.draw(node, offset, template)

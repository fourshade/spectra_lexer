""" Base module for text graphing. Defines top-level graph structures. """

from typing import Optional, Tuple

from .format import BaseHTMLFormatter, CompatHTMLFormatter, StandardHTMLFormatter
from .layout import CascadedGraphLayout, CompressedGraphLayout
from .render import NodeFactory
from ..rules import StenoRule


class StenoGraph:
    """ Formats and renders a monospaced text graph of a rule. """

    def __init__(self, factory:NodeFactory, formatter:BaseHTMLFormatter) -> None:
        self._factory = factory      # Original factory for the node tree that knows which rule created each node.
        self._formatter = formatter  # Formats the output text based on which node is selected (if any).

    def render(self, ref="", *, find_rule=False, **kwargs) -> Tuple[str, Optional[StenoRule]]:
        """ Render a graph as HTML text with an optional reference node selected.
            <ref> is a rule name if <find_rule> is True; otherwise it is an anchor href.
            Return the finished text and any valid rule selection. """
        node = self._factory.lookup_node(ref) if find_rule else self._formatter.get_node(ref)
        text = self._formatter.to_html(node, **kwargs)
        rule = self._factory.lookup_rule(node)
        return text, rule

    @classmethod
    def generate(cls, rule:StenoRule, recursive=True, compressed=True, compat=False):
        """ Make a root graph node and formatter out of <rule> and construct a graph object.
            <recursive> - If True, add sub-graphs for rules that are composed of other rules.
            <compressed> - If True, lay out the graph in a manner that squeezes nodes together as much as possible.
            <compat> - If True, use a formatter that implements text monospacing with explicit markup. """
        factory = NodeFactory(recursive=recursive)
        root = factory.make_root(rule)
        layout = CompressedGraphLayout() if compressed else CascadedGraphLayout()
        formatter_cls = CompatHTMLFormatter if compat else StandardHTMLFormatter
        formatter = formatter_cls.build(root, layout)
        return cls(factory, formatter)

from spectra_lexer.core import Component, Command, Signal
from spectra_lexer.steno import LXGraph, LXLexer
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.system import ConfigOption


class VIEWGraph:
    """ Interface for handling display and selection of text graphs. """

    @Command
    def show_generated_rule(self, rule:StenoRule) -> None:
        """ Generate a new graph from a rule and set the title. """
        raise NotImplementedError

    @Command
    def hover_character(self, row:int, col:int) -> None:
        """ Find the node owning the character at (row, col) of the graph and highlight it if nothing is selected. """
        raise NotImplementedError

    @Command
    def select_character(self, row:int, col:int) -> None:
        """ Find the node owning the character at (row, col) and select it permanently with a bright color. """
        raise NotImplementedError

    class NewTitle:
        @Signal
        def on_graph_title(self, title:str) -> None:
            raise NotImplementedError

    class NewGraph:
        @Signal
        def on_graph_output(self, text:str, scroll_to:str="top") -> None:
            raise NotImplementedError

    class RuleSelected:
        @Signal
        def on_graph_rule_selected(self, rule:StenoRule) -> None:
            raise NotImplementedError


class GraphView(Component, VIEWGraph,
                LXLexer.Output):
    """ Implementation for handling text graphs and selections. """

    recursive_graph: bool = ConfigOption("graph", "recursive", default=True,
                                         desc="Include rules that make up other rules.")
    compressed_graph: bool = ConfigOption("graph", "compressed", default=True,
                                          desc="Compress the graph vertically to save space.")

    _last_rule: StenoRule = None       # Most recent rule from lexer.
    _last_selection: StenoRule = None  # Most recent selected rule.

    def show_generated_rule(self, rule:StenoRule) -> None:
        self.engine_call(self.NewTitle, str(rule))
        self._last_rule = rule
        self._last_selection = self._make_graph(is_new=True, rules=[self._last_selection], intense=True)

    def hover_character(self, row:int, col:int) -> None:
        if self._last_selection is None:
            self._make_graph(locations=[(row, col)])

    def select_character(self, row:int, col:int) -> None:
        self._last_selection = self._make_graph(locations=[(row, col)], intense=True)

    def _make_graph(self, is_new:bool=False, **kwargs) -> StenoRule:
        """ Select a rule and format the graph with its reference highlighted. """
        if self._last_rule is not None:
            rules, text = self.engine_call(LXGraph.generate, self._last_rule,
                                           recursive=self.recursive_graph, compressed=self.compressed_graph, **kwargs)
            active = rules[0] if rules else None
            self.engine_call(self.RuleSelected, active or self._last_rule)
            # A new graph should scroll to the top by default. Otherwise don't allow the graph to scroll.
            self.engine_call(self.NewGraph, text, scroll_to="top" if is_new else None)
            return active

    # Route lexer output as a full rule display.
    on_lexer_output = show_generated_rule

from .graph import VIEWGraph
from spectra_lexer.core import Component, Command, Signal
from spectra_lexer.steno import LXBoard
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.system import ConfigOption


class VIEWBoard:
    """ Interface to draw steno board diagram elements and the description for rules. """

    @Command
    def resize(self, width:int, height:int) -> None:
        """ Tell the board layout engine when the graphical container changes size and redraw if necessary. """
        raise NotImplementedError

    class NewDiagram:
        @Signal
        def on_view_board_diagram(self, xml_data:bytes) -> None:
            """ Set the currently displayed SVG image in bytes format and redraw. """
            raise NotImplementedError


class BoardView(Component, VIEWBoard,
                VIEWGraph.RuleSelected):

    show_compound: bool = ConfigOption("board", "compound_keys", default=True,
                                       desc="Show special labels for compound keys (i.e. `f` instead of TP).")

    _last_rule: StenoRule = None  # Most recent rule shown.
    _last_ratio: float = 100      # Last known aspect ratio for board viewing area.

    def resize(self, width:int, height:int) -> None:
        self._last_ratio = width / height
        if self._last_rule is not None:
            self.on_graph_rule_selected(self._last_rule)

    def on_graph_rule_selected(self, rule:StenoRule) -> None:
        xml_data = self.engine_call(LXBoard.from_rule, rule, self._last_ratio, show_compound=self.show_compound)
        if xml_data:
            self._last_rule = rule
            self.engine_call(self.NewDiagram, xml_data)

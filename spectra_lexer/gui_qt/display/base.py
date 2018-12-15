from PyQt5.QtWidgets import QLineEdit, QWidget

from spectra_lexer import SpectraComponent
from spectra_lexer.gui_qt.display.steno_board_widget import StenoBoardWidget
from spectra_lexer.gui_qt.display.text_graph_widget import TextGraphWidget
from spectra_lexer.output.node import OutputNode
from spectra_lexer.output.text.cascaded_text import CascadedTextFormatter
from spectra_lexer.rules import StenoRule


class GUIQtDisplay(SpectraComponent):
    """ GUI operations class for displaying rules and finding the mouse position over the text graph. """

    w_title: QLineEdit             # Displays status messages and mapping of keys to word.
    w_text: TextGraphWidget        # Displays formatted text breakdown graph.
    w_desc: QLineEdit              # Displays rule description.
    w_board: StenoBoardWidget      # Displays steno board diagram.

    _last_node: OutputNode = None  # Most recent node from a mouse move event.

    def __init__(self, *widgets:QWidget):
        super().__init__()
        self.w_title, self.w_text, self.w_desc, self.w_board = widgets
        self.w_text.mouseOverCharacter.connect(self.process_mouseover)
        self.add_commands({"new_lexer_result":      self.display_title,
                           "new_output_tree":       self.display_board_info,
                           "new_output_text_graph": self.display_new_graph,
                           "set_status_message":    self.w_title.setText})
        self.add_children([CascadedTextFormatter()])

    def display_title(self, rule:StenoRule):
        """ For a new lexer result, set the title from the rule. """
        self.w_title.setText(str(rule))

    def display_board_info(self, node:OutputNode) -> None:
        """ Display basic info for a node on the steno board diagram. """
        keys, desc = node.get_board_info()
        self.w_board.show_keys(keys)
        self.w_desc.setText(desc)

    def display_new_graph(self, text:str, reset_scrollbar:bool=True) -> None:
        """ Display a finished text graph in the main text widget. """
        self.w_text.set_graph(text, reset_scrollbar)

    def process_mouseover(self, row:int, col:int) -> None:
        """ From a (row, col) character position that the mouse cursor has moved over, see whether or not
            it corresponds to a node display. If it does (and isn't the one currently shown), format it
            and display the board info and formatted text graph with that node selected. """
        node = self.engine_call("output_text_node_at", row, col)
        if node is not None:
            if node is not self._last_node:
                self.display_board_info(node)
                text = self.engine_call("output_text_format", node)
                # Make sure this doesn't affect the current scroll position.
                self.display_new_graph(text, reset_scrollbar=False)
            # Store the current node so we can avoid redraw and repeated mouseover lookups.
            self._last_node = node

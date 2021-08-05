from typing import Callable, Sequence

from PyQt5.QtWidgets import QCheckBox, QLabel, QMainWindow, QMenuBar, QSlider

from .board import BoardWidget
from .graph import GraphWidget
from .main_window_ui import Ui_MainWindow
from .search import SearchPanel, SearchResults
from .title import TitleWidget

ActionCallback = Callable[[], None]


def noargs(func:ActionCallback) -> Callable:
    """ Some Qt signals provide unwanted args to callbacks. This wrapper throws them away. """
    def run(*ignored) -> None:
        func()
    return run


class GUIHooks:
    """ Full interface for Qt GUI interaction. """

    def on_translation_edit(self) -> None:
        """ Let the user know the translation won't be parsed until Enter is pressed. """

    def on_translation_submit(self, text:str) -> None:
        """ Do a lexer query on user input text. """

    def on_search_input(self, pattern:str, pages:int) -> None:
        """ Do a translation/examples search and update the GUI. """

    def on_search_query(self, match:str, mapping:str) -> None:
        """ Do an ordinary lexer query and update the GUI. """

    def on_search_multiquery(self, match:str, mappings:Sequence[str]) -> None:
        """ Do a "best translation" lexer query and update the GUI. """

    def on_request_examples(self) -> None:
        """ Start an example search for the current rule. """

    def on_graph_action(self, node_ref:str, focused:bool) -> None:
        """ Update the graph to reflect focus on a particular node by reference. """

    def on_board_invalid(self) -> None:
        """ Declare the board invalid to get new data. Doing this on any size change is expensive (but worth it). """

    def on_board_save(self) -> None:
        """ Save the current board diagram. """


class GUIController:

    def __init__(self, search:SearchPanel, w_menubar:QMenuBar, w_title:TitleWidget,
                 w_board:BoardWidget, w_graph:GraphWidget, w_strokes:QCheckBox, w_regex:QCheckBox,
                 w_slider:QSlider, w_caption:QLabel, w_link_save:QLabel, w_link_examples:QLabel) -> None:
        self._search = search                    # Wrapper for search input and result list widgets.
        self._w_menubar = w_menubar              # Top menu bar for the main window.
        self._w_title = w_title                  # Text widget for showing status and entering manual queries.
        self._w_board = w_board                  # Board diagram container widget.
        self._w_graph = w_graph                  # HTML text graph widget.
        self._w_strokes = w_strokes              # Checkbox to choose which side of a translation to search.
        self._w_regex = w_regex                  # Checkbox to enable regular expression search.
        self._w_slider = w_slider                # Slider to control board rendering options.
        self._w_caption = w_caption              # Label with caption containing rule keys/letters/description.
        self._w_link_save = w_link_save          # Hyperlink to save diagram as file.
        self._w_link_examples = w_link_examples  # Hyperlink to show examples of the current rule.
        self._menus = {}                         # Tracks top-level menu sections by name.

    def set_input(self, pattern:str) -> None:
        self._search.update_input(pattern)

    def set_selections(self, match:str, mapping:str) -> None:
        self._search.select(match, mapping)

    def set_matches(self, matches:SearchResults, *, can_expand=False) -> None:
        self._search.update_results(matches, can_expand=can_expand)

    def set_title(self, text:str) -> None:
        self._w_title.setText(text)

    def set_loading_title(self, text:str, *, interval_ms=200) -> None:
        """ Animate <text> in the title bar as a loading message. It lasts until another title is set.
            Use a • dot moving down an ellipsis: loading...  ->  loading•..  ->  loading.•.  ->  loading..• """
        body = text.rstrip(".")
        frames = [body + b for b in ("...", "•..", ".•.", "..•")]
        self._w_title.setAnimatedText(frames, interval_ms)

    def set_caption(self, caption:str) -> None:
        """ Show a caption above the board diagram. """
        self._w_caption.setText(caption)

    def set_board(self, board:str) -> None:
        """ Load the board renderer with new SVG data. """
        self._w_board.setSvgData(board)
        self._w_link_save.setVisible(bool(board))

    def set_link_visible(self, visible:bool) -> None:
        """ Show/hide the examples link in the bottom-right corner of the diagram. """
        self._w_link_examples.setVisible(visible)

    def set_graph(self, text:str, *, focused=False) -> None:
        """ Turn on interaction and show HTML text in the graph widget. """
        self._w_graph.setGraph(text, focused=focused)

    def set_graph_plain(self, text:str) -> None:
        """ Turn off interaction and show plaintext in the graph widget. """
        self._w_graph.setPlaintext(text)

    def is_mode_strokes(self) -> bool:
        return self._w_strokes.isChecked()

    def is_mode_regex(self) -> bool:
        return self._w_regex.isChecked()

    def aspect_ratio(self) -> float:
        """ Return the width / height aspect ratio of the board widget. """
        size = self._w_board.size()
        return size.width() / size.height()

    def is_compound(self) -> bool:
        """ The board is compound if not in keys mode (slider at top, value=0). """
        return self._w_slider.value() > 0

    def shows_letters(self) -> bool:
        """ The board uses letters only if in letters mode (slider at bottom, value=2). """
        return self._w_slider.value() > 1

    def dump_board(self, filename:str) -> None:
        """ Save the current diagram to an SVG file (or other format). """
        self._w_board.saveImage(filename)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all display widgets. The title bar should be set read-only instead. """
        self._search.set_enabled(enabled)
        self._w_menubar.setEnabled(enabled)
        self._w_title.setReadOnly(not enabled)
        self._w_graph.setEnabled(enabled)
        self._w_strokes.setEnabled(enabled)
        self._w_regex.setEnabled(enabled)
        self._w_slider.setEnabled(enabled)

    def connect(self, hooks:GUIHooks) -> None:
        """ Connect Qt signals (through a lambda if none of their arguments are used). """
        self._search.searchRequested.connect(hooks.on_search_input)
        self._search.queryRequested.connect(hooks.on_search_query)
        self._search.queryAllRequested.connect(hooks.on_search_multiquery)
        self._w_title.textEdited.connect(noargs(hooks.on_translation_edit))
        self._w_title.submitted.connect(hooks.on_translation_submit)
        self._w_board.resized.connect(hooks.on_board_invalid)
        self._w_graph.selected.connect(hooks.on_graph_action)
        self._w_strokes.toggled.connect(noargs(self._search.invalidate))
        self._w_regex.toggled.connect(noargs(self._search.invalidate))
        self._w_slider.valueChanged.connect(noargs(hooks.on_board_invalid))
        self._w_link_save.linkActivated.connect(noargs(hooks.on_board_save))
        self._w_link_examples.linkActivated.connect(noargs(hooks.on_request_examples))

    def add_menu(self, heading:str) -> None:
        """ Create a menu under <heading> and add it to the menu bar if it does not exist. """
        if heading not in self._menus:
            self._menus[heading] = self._w_menubar.addMenu(heading)

    def add_menu_action(self, heading:str, text:str, func:ActionCallback) -> None:
        """ Create a menu item under <heading> with label <text> that calls <func> with no args when selected. """
        menu = self._menus[heading]
        action = menu.addAction(text)
        action.triggered.connect(noargs(func))

    def add_menu_separator(self, heading:str) -> None:
        """ Create a separator under <heading>. """
        menu = self._menus[heading]
        menu.addSeparator()


def build_gui(parent:QMainWindow) -> GUIController:
    ui = Ui_MainWindow()
    ui.setupUi(parent)
    search = SearchPanel(ui.w_input, ui.w_matches, ui.w_mappings)
    return GUIController(search, ui.w_menubar, ui.w_title, ui.w_board, ui.w_graph, ui.w_strokes, ui.w_regex,
                         ui.w_slider, ui.w_caption, ui.w_link_save, ui.w_link_examples)

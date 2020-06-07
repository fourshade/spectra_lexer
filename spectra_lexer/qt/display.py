from typing import Callable, Dict, Tuple

from PyQt5.QtWidgets import QLabel, QSlider

from spectra_lexer.qt.board import DisplayBoard
from spectra_lexer.qt.graph import DisplayGraph
from spectra_lexer.qt.title import DisplayTitle

from .svg import QtSVGData

ExamplesCallback = Callable[[str], None]
QueryCallback = Callable[[str, str], None]


class DisplayPageData:
    """ Data class that contains HTML formatted graphs, a caption, an SVG board, and a link reference. """

    def __init__(self, html_graphs:Tuple[str, str], board_caption:str, board_data:QtSVGData, link_ref:str) -> None:
        self.html_graphs = html_graphs      # Sequence of 2 HTML text graphs for this rule: [normal, bright].
        self.board_caption = board_caption  # Text caption for this rule, drawn above the board.
        self.board_data = board_data        # XML containing this rule's SVG board diagram.
        self.link_ref = link_ref            # Target ref for a link to find examples of this rule (empty if none).


EMPTY_PAGE_DATA = DisplayPageData(("", ""), "", "", "")


class DisplayController:

    _DEFAULT_PAGE_KEY = "_DEFAULT"  # Dict key for default display page (nothing selected).

    TR_DELIMITER = '->'  # Delimiter between keys and letters of translations shown in title bar.
    TR_MSG_CHANGED = "Press Enter to parse any changes."
    TR_MSG_EDELIMITERS = 'ERROR: An arrow "->" must separate the steno keys and translated text.'
    TR_MSG_EBLANK = 'ERROR: One or both sides is empty.'

    def __init__(self, title:DisplayTitle, graph:DisplayGraph, board:DisplayBoard,
                 w_caption:QLabel, w_slider:QSlider, w_link_examples:QLabel) -> None:
        self._title = title
        self._graph = graph
        self._board = board
        self._w_caption = w_caption  # Label with caption containing rule keys/letters/description.
        self._w_slider = w_slider    # Slider to control board rendering options.
        self._w_link_examples = w_link_examples  # Rule example hyperlink.
        self._page_dict = {}
        self._last_link_ref = ""
        self._last_translation = None
        self._call_example_search = None
        self._call_query = None

    def _search_examples(self) -> None:
        """ Start an example search based on the last valid link reference. """
        if self._last_link_ref:
            self._call_example_search(self._last_link_ref)

    def _send_query(self) -> None:
        """ Send a query based on the last valid translation. """
        if self._last_translation is not None:
            keys, letters = self._last_translation
            self._call_query(keys, letters)

    def _set_title(self, text:str) -> None:
        self._title.set_static_text(text)

    def _set_caption(self, caption:str) -> None:
        """ Show a caption above the board diagram. """
        self._w_caption.setText(caption)

    def _set_link_ref(self, link_ref:str) -> None:
        """ Show the link in the bottom-right corner of the diagram if examples exist. """
        self._last_link_ref = link_ref
        self._w_link_examples.setVisible(bool(link_ref))

    def _set_page(self, page:DisplayPageData, focused=False) -> None:
        """ Change the currently displayed analysis page and set its focus state. """
        self._graph.set_graph_text(page.html_graphs[focused])
        self._graph.set_focus(focused)
        self._set_caption(page.board_caption)
        self._board.set_data(page.board_data)
        self._set_link_ref(page.link_ref)

    def _clear_page(self) -> None:
        """ Clear the current translation and analysis page and turn off graph interaction. """
        self._last_translation = None
        self._set_page(EMPTY_PAGE_DATA)
        self._graph.set_plaintext("")

    def _graph_action(self, node_ref:str, focused:bool) -> None:
        """ On mouse actions, change the current analysis page to the one under <node_ref>.
            If <node_ref> is an empty string, show the default page with nothing focused. """
        if not node_ref:
            focused = False
            node_ref = self._DEFAULT_PAGE_KEY
        page = self._page_dict.get(node_ref)
        if page is not None:
            self._set_page(page, focused)

    def _on_graph_over(self, node_ref:str) -> None:
        self._graph_action(node_ref, False)

    def _on_graph_click(self, node_ref:str) -> None:
        self._graph_action(node_ref, True)

    def _on_link_click(self, *_) -> None:
        self._search_examples()

    def _on_slider_move(self, *_) -> None:
        """ On slider movements, resend the last query to get new pages rendered. """
        self._send_query()

    def _on_translation_edit(self, _:str) -> None:
        """ Display user entry instructions in the caption. """
        self._set_caption(self.TR_MSG_CHANGED)

    def _on_translation_submit(self, text:str) -> None:
        """ Display user entry errors in the caption. """
        self._clear_page()
        args = text.split(self.TR_DELIMITER, 1)
        if not len(args) == 2:
            self._set_caption(self.TR_MSG_EDELIMITERS)
            return
        keys, letters = map(str.strip, args)
        if not (keys and letters):
            self._set_caption(self.TR_MSG_EBLANK)
            return
        self.set_translation(keys, letters)
        self._send_query()

    def connect_signals(self, call_example_search:ExamplesCallback, call_query:QueryCallback) -> None:
        """ Connect all Qt signals for user actions and set the callback functions. """
        self._call_example_search = call_example_search
        self._call_query = call_query
        self._graph.connect_signals(self._on_graph_over, self._on_graph_click)
        self._board.connect_signals()
        self._title.connect_signals(self._on_translation_edit, self._on_translation_submit)
        self._w_slider.valueChanged.connect(self._on_slider_move)
        self._w_link_examples.linkActivated.connect(self._on_link_click)

    def get_board_ratio(self) -> float:
        """ Return the width / height aspect ratio of the board widget. """
        size = self._board.get_size()
        return size.width() / size.height()

    def get_board_compound(self) -> bool:
        """ The board is compound if not in keys mode (slider at top, value=0). """
        return self._w_slider.value() > 0

    def get_board_letters(self) -> bool:
        """ The board uses letters only if in letters mode (slider at bottom, value=2). """
        return self._w_slider.value() > 1

    def set_translation(self, keys:str, letters:str) -> None:
        """ Format a translation and show it in the title bar. """
        self._last_translation = [keys, letters]
        tr_text = " ".join([keys, self.TR_DELIMITER, letters])
        self._set_title(tr_text)

    def set_pages(self, page_dict:Dict[str, DisplayPageData], default:DisplayPageData) -> None:
        """ Replace the current dict of analysis pages and attempt to select the last link target. """
        self._page_dict = {self._DEFAULT_PAGE_KEY: default, **page_dict}
        last_link = self._last_link_ref
        start_ref = ""
        if last_link:
            for node_ref, page in page_dict.items():
                if page.link_ref == last_link:
                    start_ref = node_ref
                    break
        self._graph_action(start_ref, True)

    def set_status(self, text:str) -> None:
        """ Check if the status text ends in an ellipsis. If not, just show it in the title normally.
            Otherwise, animate the text with a • dot moving down the ellipsis until new text is shown:
            loading...  ->  loading•..  ->  loading.•.  ->  loading..• """
        if text.endswith("..."):
            body = text.rstrip(".")
            frames = [body + b for b in ("...", "•..", ".•.", "..•")]
            self._title.set_animated_text(frames, 200)
        else:
            self._set_title(text)

    def show_traceback(self, tb_text:str) -> None:
        """ Display a stack trace with an appropriate title. """
        self._set_title("Well, this is embarrassing...")
        self._graph.set_plaintext(tb_text)

    def set_enabled(self, enabled:bool) -> None:
        """ Enable/disable all display widgets. Invalidate the current graph and board on disable. """
        if not enabled:
            self._clear_page()
        self._title.set_enabled(enabled)
        self._graph.set_enabled(enabled)
        self._w_slider.setEnabled(enabled)

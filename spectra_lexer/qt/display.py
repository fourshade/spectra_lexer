from itertools import cycle
from typing import Callable, Dict, Sequence, Tuple

from PyQt5.QtCore import QTimer, QUrl
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtWidgets import QLabel, QLineEdit, QSlider

from .file import save_file_dialog
from .svg import QtSVGData, SVGEngine
from .widgets import HyperlinkTextBrowser, PictureWidget

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


class DisplayTitle:
    """ Wrapper for title bar widget that displays plaintext as well as simple text animations. """

    def __init__(self, w_title:QLineEdit) -> None:
        self._w_title = w_title
        self._anim_timer = QTimer(w_title)  # Animation timer for loading messages.
        self._call_on_submit = None

    def _on_submit_text(self) -> None:
        """ Submit the title bar text to the callback. """
        text = self._w_title.text()
        self._call_on_submit(text)

    def connect_signals(self, on_edit:Callable[[str], None], on_submit:Callable[[str], None]) -> None:
        """ Connect Qt signals and set callback functions. """
        self._call_on_submit = on_submit
        self._w_title.textEdited.connect(on_edit)
        self._w_title.returnPressed.connect(self._on_submit_text)

    def set_enabled(self, enabled:bool) -> None:
        """ The title bar should be set read-only instead of disabled to continue showing status messages. """
        self._w_title.setReadOnly(not enabled)

    def set_static_text(self, text:str) -> None:
        """ Stop any animation and show normal text in the title bar. """
        self._anim_timer.stop()
        self._w_title.setText(text)

    def set_animated_text(self, text_items:Sequence[str], delay_ms:int) -> None:
        """ Set the widget text to animate over <text_items> on a timed cycle.
            The first item is shown immediately, then a new one is shown every <delay_ms> milliseconds. """
        if text_items:
            show_next_item = map(self._w_title.setText, cycle(text_items)).__next__
            show_next_item()
            self._anim_timer.timeout.connect(show_next_item)
            self._anim_timer.start(delay_ms)


class DisplayGraph:
    """ Formatted text widget for displaying a monospaced HTML graph of the breakdown of text by steno rules.
        May also display plaintext output such as error messages and exceptions when necessary. """

    def __init__(self, w_graph:HyperlinkTextBrowser) -> None:
        self._w_graph = w_graph
        self._mouse_enabled = False  # If True, all graph mouse actions are disabled.
        self._has_focus = False      # If True, freeze focus on the current page and do not allow mouseover signals.
        self._call_on_mouse_over = None
        self._call_on_mouse_click = None

    def _on_link_over(self, url:QUrl) -> None:
        """ If the graph is enabled, send the fragment string of the URL under the cursor.
            When we move off of a link, this will be sent with an empty string.
            Do not allow mouseover signals if focus is active. """
        if self._mouse_enabled and not self._has_focus:
            self._call_on_mouse_over(url.fragment())

    def _on_link_click(self, url:QUrl) -> None:
        """ If the graph is enabled, send the fragment string of the clicked URL.
            When we click something that isn't a link, this will be sent with an empty string. """
        if self._mouse_enabled:
            self._call_on_mouse_click(url.fragment())

    def connect_signals(self, on_mouse_over:Callable[[str], None], on_mouse_click:Callable[[str], None]) -> None:
        """ Connect Qt signals and set callback functions. """
        self._call_on_mouse_over = on_mouse_over
        self._call_on_mouse_click = on_mouse_click
        self._w_graph.linkOver.connect(self._on_link_over)
        self._w_graph.linkClicked.connect(self._on_link_click)

    def set_enabled(self, enabled:bool) -> None:
        self._w_graph.setEnabled(enabled)

    def set_focus(self, enabled:bool) -> None:
        """ Set the focus state of the graph. Mouseover signals will be suppressed when focus is active. """
        self._has_focus = enabled

    def set_graph_text(self, text:str) -> None:
        """ Enable graph interaction and replace the current text with new HTML formatted graph text. """
        self._mouse_enabled = True
        self._w_graph.setHtml(text, no_scroll=True)

    def set_plaintext(self, text:str) -> None:
        """ Disable graph interaction and replace the current text with new plaintext. """
        self._mouse_enabled = False
        self._w_graph.clear()
        self._w_graph.setCurrentCharFormat(QTextCharFormat())
        self._w_graph.append(text)


class DisplayBoard:
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    def __init__(self, w_board:PictureWidget, w_link_save:QLabel) -> None:
        self._w_board = w_board          # Board diagram container widget.
        self._w_link_save = w_link_save  # Hyperlink to save diagram as file.
        self._svg = SVGEngine()

    def get_size(self) -> Tuple[float, float]:
        """ Return the size of the board widget. """
        return self._w_board.width(), self._w_board.height()

    def _draw_board(self) -> None:
        """ Render the diagram to the board widget. """
        width, height = self.get_size()
        bounds = self._svg.best_fit(width, height)
        with self._w_board as target:
            self._svg.render(target, bounds)

    def _on_resize(self, *_) -> None:
        """ Redraw the board on any size change. """
        self._draw_board()

    def _on_link_click(self, *_) -> None:
        """ Save the current diagram to an SVG file on link click. """
        filename = save_file_dialog(self._w_board, "Save File", "svg|png", "board.svg")
        if filename:
            if filename.endswith('png'):
                self._svg.save_png(filename)
            else:
                self._svg.save(filename)

    def connect_signals(self) -> None:
        """ Connect Qt signals and set callback functions. """
        self._w_board.resized.connect(self._on_resize)
        self._w_link_save.linkActivated.connect(self._on_link_click)

    def set_data(self, data:QtSVGData) -> None:
        """ Load the renderer with new SVG data and redraw the board. """
        self._svg.load(data)
        self._w_link_save.setVisible(bool(data))
        self._draw_board()


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
        width, height = self._board.get_size()
        return width / height

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

from itertools import cycle
from typing import Sequence, Tuple

from PyQt5.QtCore import pyqtSignal, QObject, QRectF, QTimer, QUrl
from PyQt5.QtGui import QPainter, QPicture, QTextCharFormat
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QLabel, QLineEdit

from .widgets import HyperlinkTextBrowser, PictureWidget


class _TitleWrapper(QObject):
    """ Wrapper for title bar widget that displays translations as well as loading/status with simple text animations.
        Also allows manual lexer queries by editing translations directly. """

    sig_edit_translation = pyqtSignal([list])  # Sent with a [keys, letters] translation on a valid edit.

    _anim_iter = cycle([""])  # Animation string iterator. Should repeat indefinitely.

    def __init__(self, w_title:QLineEdit, tr_delim:str=" -> ") -> None:
        super().__init__()
        self._w_title = w_title
        self._tr_delim = tr_delim      # Delimiter between keys and letters of translations shown in title bar.
        self._timer = QTimer(self)     # Animation timer for loading messages.
        self._timer.timeout.connect(self._animate)
        w_title.textEdited.connect(self._edit_translation)

    def _edit_translation(self, text:str) -> None:
        """ Parse the title bar text as a translation and send the signal if it is valid. """
        parts = text.split(self._tr_delim)
        if len(parts) == 2:
            translation = [p.strip() for p in parts]
            self.sig_edit_translation.emit(translation)

    def set_translation(self, translation:list) -> None:
        """ Format a translation and show it in the title bar. """
        text = self._tr_delim.join(translation)
        self.set_static_text(text)

    def set_static_text(self, text:str):
        """ Stop any animation and show normal text in the title bar. """
        self._timer.stop()
        self._w_title.setText(text)

    def set_animated_text(self, text_items:Sequence[str], delay_ms:int) -> None:
        """ Set the widget text to animate over <text_items> on a timed cycle.
            The first item is shown immediately, then a new one is shown every <delay_ms> milliseconds. """
        assert text_items
        self._anim_iter = cycle(text_items)
        self._animate()
        self._timer.start(delay_ms)

    def _animate(self) -> None:
        """ Set the widget text to the next item in the string iterator. """
        text = next(self._anim_iter)
        self._w_title.setText(text)

    def set_enabled(self, enabled:bool) -> None:
        """ The title bar should be set read-only instead of disabled to continue showing status messages. """
        self._w_title.setReadOnly(not enabled)


class _GraphWrapper(QObject):
    """ Formatted text widget for displaying a monospaced HTML graph of the breakdown of text by steno rules.
        May also display plaintext output such as error messages and exceptions when necessary. """

    sig_ref_over = pyqtSignal([str])   # Sent with a node reference when the mouse moves over a new one.
    sig_ref_click = pyqtSignal([str])  # Sent with a node reference when the mouse clicks one.

    def __init__(self, w_graph:HyperlinkTextBrowser) -> None:
        super().__init__()
        self._w_graph = w_graph
        self._graph_enabled = False  # Does moving the mouse over the text do anything?
        w_graph.linkOver.connect(self._on_hover_link)
        w_graph.linkClicked.connect(self._on_click_link)

    def add_plaintext(self, text:str) -> None:
        """ Add plaintext to the widget. If it currently contains a graph, disable it and reset the formatting. """
        if self._graph_enabled:
            self._graph_enabled = False
            self._w_graph.clear()
            self._w_graph.setCurrentCharFormat(QTextCharFormat())
        self._w_graph.append(text)

    def set_graph_text(self, text:str) -> None:
        """ Enable graph interaction and replace the current text with new HTML formatted graph text. """
        self._graph_enabled = True
        self._w_graph.setHtml(text, no_scroll=True)

    def set_enabled(self, enabled:bool) -> None:
        """ Blank out the graph on disable. """
        self._graph_enabled = enabled
        if not enabled:
            self._w_graph.clear()

    def _on_hover_link(self, url:QUrl) -> None:
        self._on_link_signal(self.sig_ref_over, url)

    def _on_click_link(self, url:QUrl) -> None:
        self._on_link_signal(self.sig_ref_click, url)

    def _on_link_signal(self, sig, url:QUrl) -> None:
        if self._graph_enabled:
            sig.emit(url.fragment())


class _BoardWrapper(QObject):
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    sig_activate_link = pyqtSignal()  # Sent when examples link is clicked.
    sig_new_ratio = pyqtSignal([float])  # Sent on board resize with the new aspect ratio.

    def __init__(self, w_board:PictureWidget) -> None:
        """ Create the renderer and examples link. """
        super().__init__()
        self._w_board = w_board
        self._w_link = QLabel(w_board)  # Rule example hyperlink.
        self._w_link.linkActivated.connect(self._on_link_click)
        self._renderer = QSvgRenderer()  # XML SVG renderer.
        w_board.resized.connect(self._on_resize)

    def _on_link_click(self, *args) -> None:
        """ Send the examples link click signal with no args (the GUI already knows what it links to). """
        self.sig_activate_link.emit()

    def set_link(self, ref="") -> None:
        """ Show the link in the bottom-right corner of the diagram if examples exist.
            Any currently linked rule is already known to the GUI, so the link href doesn't matter. """
        self._w_link.setText("<a href='dummy'>More Examples</a>")
        self._w_link.setVisible(bool(ref))

    def _on_resize(self) -> None:
        """ Reposition the link and send the new widget aspect ratio on any size change. """
        width, height = self.get_size()
        self._w_link.move(width - 75, height - 18)
        self._draw_board()
        self.sig_new_ratio.emit(width / height)

    def get_size(self) -> Tuple[int, int]:
        """ Return the current width and height of the board widget in pixels. """
        width = self._w_board.width()
        height = self._w_board.height()
        return width, height

    def set_data(self, xml_data:bytes=b"") -> None:
        """ Load the renderer with raw XML data containing the elements to draw, then render the new board. """
        self._renderer.load(xml_data)
        self._draw_board()

    def _draw_board(self) -> None:
        """ Render the diagram on a new picture and immediately repaint the board. """
        gfx = QPicture()
        with QPainter(gfx) as p:
            # Set anti-aliasing on for best quality.
            p.setRenderHints(QPainter.Antialiasing)
            bounds = self._get_draw_bounds()
            self._renderer.render(p, bounds)
        self._w_board.setPicture(gfx)

    def _get_draw_bounds(self) -> QRectF:
        """ Return the bounding box needed to center everything in the widget at maximum scale. """
        _, _, vw, vh = self._renderer.viewBoxF().getRect()
        if vw and vh:
            width, height = self.get_size()
            scale = min(width / vw, height / vh)
            fw, fh = vw * scale, vh * scale
            ox = (width - fw) / 2
            oy = (height - fh) / 2
            return QRectF(ox, oy, fw, fh)
        else:
            # If no valid viewbox is defined, use the widget's natural size.
            return QRectF(0, 0, *self.get_size())

    def set_enabled(self, enabled:bool) -> None:
        """ Blank out the link on disable. """
        if not enabled:
            self.set_link()


class _CaptionWrapper:

    def __init__(self, w_caption:QLabel) -> None:
        self._w_caption = w_caption  # Label with caption containing rule keys/letters/description.

    def set_caption(self, caption="") -> None:
        """ Show a caption above the board diagram. """
        self._w_caption.setText(caption)


class DisplayController(QObject):

    def __init__(self, w_title:QLineEdit, w_graph:HyperlinkTextBrowser,
                 w_board:PictureWidget, w_caption:QLabel) -> None:
        super().__init__()
        self._title = _TitleWrapper(w_title)
        self._graph = _GraphWrapper(w_graph)
        self._board = _BoardWrapper(w_board)
        self._caption = _CaptionWrapper(w_caption)
        self.sig_edit_translation = self._title.sig_edit_translation
        self.sig_over_graph = self._graph.sig_ref_over
        self.sig_click_graph = self._graph.sig_ref_click
        self.sig_activate_link = self._board.sig_activate_link
        self.sig_board_ratio = self._board.sig_new_ratio
        self.set_graph_text = self._graph.set_graph_text
        self.set_translation = self._title.set_translation
        self.get_board_size = self._board.get_size
        self.set_board_xml = self._board.set_data
        self.set_link = self._board.set_link
        self.set_caption = self._caption.set_caption

    def set_enabled(self, enabled:bool) -> None:
        self._title.set_enabled(enabled)
        self._graph.set_enabled(enabled)
        self._board.set_enabled(enabled)

    def show_traceback(self, tb_text:str) -> None:
        """ Display a stack trace. """
        self._title.set_static_text("Well, this is embarrassing...")
        self._graph.add_plaintext(tb_text)

    def set_status(self, text:str) -> None:
        """ Check if the status text ends in an ellipsis. If not, just show the text normally.
            Otherwise, animate the text with a • dot moving down the ellipsis until new text is shown:
            loading...  ->  loading•..  ->  loading.•.  ->  loading..• """
        if text.endswith("..."):
            body = text.rstrip(".")
            frames = [body + b for b in ("...", "•..", ".•.", "..•")]
            self._title.set_animated_text(frames, 200)
        else:
            self._title.set_static_text(text)

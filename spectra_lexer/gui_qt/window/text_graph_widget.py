from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtWidgets import QTextBrowser


class TextGraphWidget(QTextBrowser):
    """ Formatted text widget for displaying a monospaced HTML graph of the breakdown of text by steno rules.
        May also display plaintext output such as error messages and exceptions when necessary. """

    sig_over_ref = pyqtSignal([str])   # Sent with a node's reference when the mouse moves over a new one.
    sig_click_ref = pyqtSignal([str])  # Sent with a node's reference when the mouse clicks one.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._last_ref = ""          # Last graph node reference the mouse was over.
        self._graph_enabled = False  # Does moving the mouse over the text do anything?
        self.highlighted.connect(self._hover_link)

    def add_plaintext(self, text:str) -> None:
        """ Add plaintext to the widget. If it currently contains a graph, disable it and reset the formatting. """
        if self._graph_enabled:
            self._graph_enabled = False
            self.clear()
            self.setCurrentCharFormat(QTextCharFormat())
        self.append(text)

    def set_graph_text(self, text:str) -> None:
        """ Enable graph interaction and replace the current text with new HTML formatted graph text. """
        self._graph_enabled = True
        # Scroll position is automatically reset to the top when the text is set in this widget.
        # The scroll values must be manually saved and restored to negate any scrolling effect.
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self.setHtml(text)
        sx.setValue(px)
        sy.setValue(py)

    def _hover_link(self, url:QUrl) -> None:
        """ In general, if the mouse has moved over a new node reference, we save it and send the mouseover signal.
            An empty string is given when the mouse moves off a reference, which counts as a deselection.
            However, mouseovers are error-prone; there are unavoidable breaks between characters in a column.
            To avoid twitchy selection/deselection, we only send mouseover signals when the reference isn't empty. """
        if self._graph_enabled:
            ref = self._last_ref = url.toString()
            if ref:
                self.sig_over_ref.emit(ref)

    def leaveEvent(self, *args) -> None:
        """ When the mouse leaves the widget entirely, send a signal to reset the node reference. """
        super().leaveEvent(*args)
        if self._graph_enabled:
            self.sig_over_ref.emit("")

    def mousePressEvent(self, *args) -> None:
        """ Mouse clicks always send a signal to select the last node that received a hover event.
            If the node reference is empty, it is effectively a deselection. """
        super().mousePressEvent(*args)
        if self._graph_enabled:
            self.sig_click_ref.emit(self._last_ref)

from typing import Callable

from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtWidgets import QTextBrowser

ActionCallback = Callable[[str, bool], None]


class GraphWidget(QTextBrowser):
    """ Formatted text widget that sends signals on mouse interactions with hyperlinks. """

    linkOver = pyqtSignal([QUrl])     # Sent when the mouse moves over a new link.
    linkClicked = pyqtSignal([QUrl])  # Sent when the mouse clicks a link.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._url = QUrl()  # Current link URL the mouse is over
        self.highlighted.connect(self._hoverLink)

    def _hoverLink(self, url:QUrl) -> None:
        """ In general, if the mouse has moved over a new hyperlink, we save it and send the mouseover signal.
            An empty URL is given when the mouse moves off a hyperlink, which counts as a deselection.
            However, mouseovers are error-prone; there are unavoidable breaks between characters in a column.
            To avoid twitchy selection/deselection, we only send mouseover signals when the reference isn't empty. """
        self._url = url
        if url.toString():
            self.linkOver.emit(url)

    def leaveEvent(self, *args) -> None:
        """ If the mouse leaves the widget and there is an active URL, reset it. """
        super().leaveEvent(*args)
        if self._url.toString():
            self._url = QUrl()
            self.linkOver.emit(self._url)

    def mousePressEvent(self, *args) -> None:
        """ Mouse clicks always send a signal with the last URL that received a hover event. """
        super().mousePressEvent(*args)
        self.linkClicked.emit(self._url)


class GraphPanel:
    """ GUI panel for displaying a monospaced HTML graph of the breakdown of text by steno rules.
        May also display plaintext output such as error messages and exceptions when necessary. """

    def __init__(self, w_graph:GraphWidget) -> None:
        self._w_graph = w_graph
        self._mouse_enabled = False  # If True, all graph mouse actions are disabled.
        self._has_focus = False      # If True, freeze focus on the current page and do not allow mouseover signals.
        self._call_on_graph_action = None

    def _send_action(self, url:QUrl) -> None:
        """ Call back with the fragment string of the URL under the cursor and the focus state. """
        self._call_on_graph_action(url.fragment(), self._has_focus)

    def _on_link_over(self, url:QUrl) -> None:
        """ If the graph is enabled, send the fragment string of the URL under the cursor.
            When we move off of a link, this will be sent with an empty string.
            Do not allow mouseover signals if focus is active. """
        if self._mouse_enabled and not self._has_focus:
            self._send_action(url)

    def _on_link_click(self, url:QUrl) -> None:
        """ If the graph is enabled, send the fragment string of the clicked URL and set focus on it.
            When we click something that isn't a link, this will be sent with an empty string. """
        if self._mouse_enabled:
            self._has_focus = not url.isEmpty()
            self._send_action(url)

    def connect_signals(self, on_graph_action:ActionCallback) -> None:
        """ Connect Qt signals and set the callback function. """
        self._call_on_graph_action = on_graph_action
        self._w_graph.linkOver.connect(self._on_link_over)
        self._w_graph.linkClicked.connect(self._on_link_click)

    def set_enabled(self, enabled:bool) -> None:
        self._w_graph.setEnabled(enabled)

    def set_focus(self, enabled:bool) -> None:
        """ Set the focus state of the graph. Mouseover signals will be suppressed when focus is active. """
        self._has_focus = enabled

    def set_html(self, text:str) -> None:
        """ Enable graph interaction and replace the current text with new HTML formatted graph text.
            The scroll values must be manually saved and restored to negate any scrolling effect. """
        self._mouse_enabled = True
        sx = self._w_graph.horizontalScrollBar()
        sy = self._w_graph.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self._w_graph.setHtml(text)
        sx.setValue(px)
        sy.setValue(py)

    def set_plaintext(self, text:str) -> None:
        """ Disable graph interaction and replace the current text with new plaintext. """
        self._mouse_enabled = False
        self._has_focus = False
        self._w_graph.clear()
        self._w_graph.setCurrentCharFormat(QTextCharFormat())
        self._w_graph.append(text)

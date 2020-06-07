from typing import Callable

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QTextCharFormat

from .widgets import HyperlinkTextBrowser


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

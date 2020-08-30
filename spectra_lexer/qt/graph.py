from PyQt5.QtCore import QUrl, pyqtSignal
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtWidgets import QTextBrowser


class GraphWidget(QTextBrowser):
    """ GUI panel for displaying a monospaced HTML graph of the breakdown of text by steno rules.
        May also display plaintext output such as error messages and exceptions when necessary. """

    selected = pyqtSignal([str, bool])  # Emitted with the ref string under the cursor and the focus state.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._ref = ''               # Current link ref the mouse is over.
        self._mouse_enabled = False  # If True, all graph mouse actions are disabled.
        self._has_focus = False      # If True, freeze focus on the current page and do not allow mouseover signals.
        self.highlighted.connect(self._on_highlighted)

    def _select(self) -> None:
        """ If the mouse is enabled, emit the selection with the ref string under the cursor and the focus state. """
        if self._mouse_enabled:
            self.selected.emit(self._ref, self._has_focus)

    def _on_highlighted(self, url:QUrl) -> None:
        """ In general, if the mouse has moved over a new hyperlink, we save the fragment and send a mouseover action.
            An empty URL is given when the mouse moves off a hyperlink, which counts as a deselection.
            However, mouseovers are error-prone; there are unavoidable breaks between characters in a column.
            To avoid twitchy selection/deselection, we only send mouseover signals when the reference isn't empty. """
        self._ref = ref = url.fragment()
        if ref and not self._has_focus:
            self._select()

    def leaveEvent(self, _) -> None:
        """ If the mouse leaves the widget and there is an active URL, reset it. """
        if not self._has_focus:
            self._ref = ''
            self._select()

    def mousePressEvent(self, _) -> None:
        """ When we click a link, send its ref string and set focus on it.
            When we click anything else, reset the focus. """
        self._has_focus = bool(self._ref)
        self._select()

    def setGraph(self, text:str, *, focused=False) -> None:
        """ Enable graph interaction and replace the current text with new HTML formatted graph text.
            Mouseover signals will be suppressed when focus is active.
            The scroll values must be manually saved and restored to negate any scrolling effect. """
        self._mouse_enabled = True
        self._has_focus = focused
        sx = self.horizontalScrollBar()
        sy = self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self.setHtml(text)
        sx.setValue(px)
        sy.setValue(py)

    def setPlaintext(self, text:str) -> None:
        """ Disable graph interaction and replace the current text with new plaintext. """
        self._mouse_enabled = False
        self._has_focus = False
        self.clear()
        self.setCurrentCharFormat(QTextCharFormat())
        self.append(text)

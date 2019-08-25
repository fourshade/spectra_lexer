from PyQt5.QtCore import pyqtSignal, QUrl
from PyQt5.QtGui import QTextCharFormat
from PyQt5.QtWidgets import QTextBrowser


class TextGraphWidget(QTextBrowser):
    """ Formatted text widget meant to display a monospaced HTML text graph of the breakdown of English text
        by steno rules as well as plaintext interpreter output such as error messages and exceptions. """

    _last_ref: str = ""
    _mouse_enabled: bool = True  # Does moving the mouse over the text do anything?

    def __init__(self, *args):
        super().__init__(*args)
        self.highlighted.connect(self.hover_link)

    def set_plaintext(self, text:str) -> None:
        """ Add plaintext to the widget. If it was in interactive mode before, completely replace the text instead. """
        if self._mouse_enabled:
            self._mouse_enabled = False
            self.setCurrentCharFormat(QTextCharFormat())
        else:
            text = f"{self.toPlainText()}\n{text}"
        self.setPlainText(text)

    def set_interactive_text(self, text:str, *, scroll_to:str=None) -> None:
        """ Enable the mouse and replace the current text with new HTML formatted text.
            Optionally <scroll_to> the "top", or don't if scroll_to=None. """
        self._mouse_enabled = True
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        self.setHtml(text)
        # Scroll position is automatically reset to the top when the text is set in this widget.
        if scroll_to is None:
            # The scroll values must be manually restored to negate any scrolling effect.
            sx.setValue(px)
            sy.setValue(py)

    def hover_link(self, url:QUrl) -> None:
        """ Mouseovers are error-prone, so they only select new targets with actual rules. """
        if self._mouse_enabled:
            s = self._last_ref = url.toString()
            if s:
                self.graphOver.emit(s)

    def leaveEvent(self, *args) -> None:
        """ Treat a mouse leave event as a mouseover on nothing (which is usually blocked). """
        super().leaveEvent(*args)
        if self._mouse_enabled:
            self.graphOver.emit("")

    def mousePressEvent(self, *args) -> None:
        """ Mouse clicks always select their target, even if that target is nothing.
            Don't pass the event along to parents (unless disabled); they will tend to do their own selections. """
        if self._mouse_enabled:
            self.graphClick.emit(self._last_ref)
        else:
            super().mousePressEvent(*args)

    # Signals
    graphOver = pyqtSignal([str])
    graphClick = pyqtSignal([str])

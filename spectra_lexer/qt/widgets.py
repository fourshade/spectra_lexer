""" Qt widget subclasses with essential functionality for the GUI.
    Usually these are only necessary if an event method must be overridden. Otherwise, wrappers are used. """

from typing import List

from PyQt5.QtCore import pyqtSignal, QItemSelection, QStringListModel, Qt, QUrl
from PyQt5.QtGui import QPainter, QPicture, QWheelEvent
from PyQt5.QtWidgets import QListView, QTextBrowser, QWidget


class PictureWidget(QWidget):
    """ Simple widget that paints a saved QPicture on every paint request. """

    resized = pyqtSignal()  # Sent on widget resize.

    _picture: QPicture = None  # Last saved picture rendering.

    def setPicture(self, picture:QPicture=None) -> None:
        """ Set a new picture (or clear it) and immediately repaint the widget. """
        self._picture = picture
        self.update()

    def paintEvent(self, *args) -> None:
        """ Paint the saved picture (if any) on this widget when GUI repaint occurs. """
        if self._picture is not None:
            self._picture.play(QPainter(self))

    def resizeEvent(self, *args) -> None:
        """ Send a signal on any size change. """
        self.resized.emit()


class HyperlinkTextBrowser(QTextBrowser):
    """ Formatted text widget that sends signals on mouse interactions with hyperlinks. """

    linkOver = pyqtSignal([QUrl])     # Sent when the mouse moves over a new link.
    linkClicked = pyqtSignal([QUrl])  # Sent when the mouse clicks a link.

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._url = QUrl()  # Current link URL the mouse is over
        self.highlighted.connect(self._hoverLink)

    def setHtml(self, text:str, *, no_scroll=False) -> None:
        """ Scroll position is automatically reset to the top when the text is set in this widget.
            The scroll values must be manually saved and restored to negate any scrolling effect. """
        sx, sy = self.horizontalScrollBar(), self.verticalScrollBar()
        px, py = sx.value(), sy.value()
        super().setHtml(text)
        if no_scroll:
            sx.setValue(px)
            sy.setValue(py)

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


class StringListView(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    itemSelected = pyqtSignal([str])  # Sent when a new list item is selected, with that item's string value.

    def __init__(self, *args, min_font_size=5, max_font_size=100) -> None:
        super().__init__(*args)
        self._min_font_size = min_font_size  # Minimum font size for list items in points.
        self._max_font_size = max_font_size  # Maximum font size for list items in points.
        self.setModel(QStringListModel([]))

    def setItems(self, str_list:List[str]) -> None:
        """ Replace the list of items. This deselects every item, even ones that didn't change. """
        self.model().setStringList(str_list)

    def selectByValue(self, value:str=None, *, center_selection=False) -> None:
        """ Programmatically select a specific item by value if it exists. If it doesn't, clear the selection.
            Suppress signals to keep from tripping the selectionChanged event. """
        self.blockSignals(True)
        try:
            model = self.model()
            list_idx = model.stringList().index(value)
            model_idx = model.index(list_idx, 0)
            sel_model = self.selectionModel()
            sel_model.select(model_idx, sel_model.SelectCurrent)
            if center_selection:
                # Put the selection as close as possible to the center of the viewing area.
                self.scrollTo(model_idx, self.PositionAtCenter)
        except ValueError:
            self.clearSelection()
        self.blockSignals(False)

    def selectedValue(self) -> str:
        """ Return the value of the first selected item (if any). """
        idxs = self.selectedIndexes()
        if not idxs:
            return ""
        return self.model().data(idxs[0], Qt.DisplayRole)

    def selectionChanged(self, selected:QItemSelection, deselected:QItemSelection) -> None:
        """ Send a signal on selection change with the first selected item (if any). """
        super().selectionChanged(selected, deselected)
        item_str = self.selectedValue()
        if item_str:
            self.itemSelected.emit(item_str)

    def wheelEvent(self, event:QWheelEvent) -> None:
        """ Change the font size if Ctrl is held down, otherwise scroll the list as usual. """
        if not event.modifiers() & Qt.ControlModifier:
            return super().wheelEvent(event)
        delta = event.angleDelta().y()
        sign = (delta // abs(delta)) if delta else 0
        font = self.font()
        new_size = font.pointSize() + sign
        if self._min_font_size <= new_size <= self._max_font_size:
            font.setPointSize(new_size)
            self.setFont(font)
        event.accept()

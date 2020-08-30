""" Qt widget subclasses with essential functionality for the GUI.
    Usually these are only necessary if an event method must be overridden. Otherwise, wrappers are used. """

from typing import Iterable

from PyQt5.QtCore import pyqtSignal, QItemSelection, QPoint, QRect, QStringListModel, Qt, QUrl
from PyQt5.QtGui import QContextMenuEvent, QPainter, QPicture, QWheelEvent
from PyQt5.QtWidgets import QListView, QTextBrowser, QWidget


class PictureWidget(QWidget):
    """ Generic widget using a QPicture as a paint buffer. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._picture = QPicture()  # Last saved picture rendering.

    def __enter__(self) -> QPicture:
        """ Reset the current picture, size it to match the widget, and return it for rendering. """
        self._picture = picture = QPicture()
        rect = QRect()
        rect.setSize(self.size())
        picture.setBoundingRect(rect)
        return picture

    def __exit__(self, *_) -> None:
        """ Repaint the widget after rendering is complete. """
        self.update()

    def paintEvent(self, *_) -> None:
        """ Paint the saved picture on this widget when GUI repaint occurs. """
        with QPainter(self) as p:
            self._picture.play(p)

    # should be inherited from a: """ Mixin to send a signal on a context menu request (right-click). """

    contextMenuRequest = pyqtSignal([QPoint])

    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        pos = event.globalPos()
        self.contextMenuRequest.emit(pos)

    # should be inherited from a: """ Mixin to send a signal on any widget size change. """

    resized = pyqtSignal()

    def resizeEvent(self, *_) -> None:
        self.resized.emit()


class HyperlinkTextBrowser(QTextBrowser):
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


class StringListView(QListView):
    """ Simple QListView extension with strings that sends a signal when the selection has changed. """

    itemSelected = pyqtSignal([str])  # Sent when a new list item is selected, with that item's string value.

    def __init__(self, *args, min_font_size=5, max_font_size=100) -> None:
        super().__init__(*args)
        self._min_font_size = min_font_size  # Minimum font size for list items in points.
        self._max_font_size = max_font_size  # Maximum font size for list items in points.
        self.setModel(QStringListModel([]))

    def setItems(self, str_iter:Iterable[str]) -> None:
        """ Replace the list of items. This deselects every item, even ones that didn't change. """
        self.model().setStringList(str_iter)

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

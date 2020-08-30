from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QContextMenuEvent, QGuiApplication, QImage, QPaintDevice, QPainter, QPixmap
from PyQt5.QtWidgets import QMenu, QWidget

from .svg import QtSVGData, SVGEngine


class Clipboard:
    """ Wrapper for system clipboard operations. """

    def __init__(self) -> None:
        self._qclipboard = QGuiApplication.clipboard()  # System clipboard singleton.

    def copy(self, obj:object) -> None:
        """ Copy an object to the clipboard. """
        if isinstance(obj, str):
            self._qclipboard.setText(obj)
        elif isinstance(obj, QImage):
            self._qclipboard.setImage(obj)
        elif isinstance(obj, QPixmap):
            self._qclipboard.setPixmap(obj)
        else:
            raise TypeError("Object type is not supported by the clipboard.")


class BoardWidget(QWidget):
    """ Displays SVG diagrams of all of the keys that make up one or more steno strokes. """

    PAINT_BG = QColor(0, 0, 0, 0)         # Transparent background for widget painting.
    COPY_BG = QColor(255, 255, 255, 255)  # White background for the clipboard.

    resized = pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._svg = SVGEngine()        # SVG rendering engine.
        self._clipboard = Clipboard()  # System clipboard wrapper.
        self._pixmap = QPixmap()       # Last saved rendering.
        self._ctx_menu = QMenu(self)   # Context menu to copy diagram to clipboard.
        self._ctx_menu_on = False
        self._ctx_menu.addAction("Copy Image", self.copyImage)

    def _paint_to(self, target:QPaintDevice) -> None:
        """ Paint the saved rendering to <target>. """
        with QPainter(target) as p:
            p.drawPixmap(0, 0, self._pixmap)

    def _render(self) -> None:
        """ Render the diagram based on the current size and repaint the widget. """
        self._pixmap = pixmap = QPixmap(self.size())
        pixmap.fill(self.PAINT_BG)
        self._svg.render_fit(pixmap)
        self.update()

    def setSvgData(self, data:QtSVGData) -> None:
        """ Set new SVG image data and render it. """
        self._svg.loads(data)
        self._ctx_menu_on = bool(data)
        self._render()

    def copyImage(self) -> None:
        """ Copy the current rendering to the clipboard with a solid background. """
        pcopy = QPixmap(self._pixmap.size())
        pcopy.fill(self.COPY_BG)
        self._paint_to(pcopy)
        self._clipboard.copy(pcopy)

    def saveImage(self, filename:str) -> None:
        """ Save the current rendering to an image file. Format is determined by the file extension. """
        ext = filename[-3:]
        if ext.lower() == 'svg':
            self._svg.dump(filename)
        else:
            self._pixmap.save(filename, ext)

    def paintEvent(self, _) -> None:
        """ Repaint the widget with the saved rendering. """
        self._paint_to(self)

    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        """ Send a signal on a context menu request (right-click). """
        if self._ctx_menu_on:
            pos = event.globalPos()
            self._ctx_menu.popup(pos)

    def resizeEvent(self, _) -> None:
        """ Rerender on any widget size change and send a signal. """
        self._render()
        self.resized.emit()

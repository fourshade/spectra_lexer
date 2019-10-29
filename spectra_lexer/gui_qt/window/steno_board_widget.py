from PyQt5.QtCore import pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QPicture
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QLabel, QWidget


class StenoBoardWidget(QWidget):
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    sig_activate_link = pyqtSignal()     # Sent when examples link is clicked.
    sig_new_ratio = pyqtSignal([float])  # Sent on board resize with the new aspect ratio.

    def __init__(self, *args) -> None:
        """ Create the renderer and examples link. """
        super().__init__(*args)
        self._renderer = QSvgRenderer()  # XML SVG renderer.
        self._gfx = QPicture()           # Last recorded rendering of the steno board.
        self._w_link = QLabel(self)      # Rule example hyperlink.
        self._w_link.linkActivated.connect(self._click_link)
        self.set_link()

    def set_link(self, ref="") -> None:
        """ Show the link in the bottom-right corner of the diagram if examples exist.
            Any currently linked rule is already known to the GUI, so the link href doesn't matter. """
        self._w_link.setText("<a href='dummy'>More Examples</a>")
        self._w_link.setVisible(bool(ref))

    def _click_link(self, *args) -> None:
        """ Send the examples link click signal with no args (the GUI already knows what it links to). """
        self.sig_activate_link.emit()

    def set_data(self, xml_data:bytes=b"") -> None:
        """ Load the renderer with raw XML data containing the elements to draw, then render the new board. """
        self._renderer.load(xml_data)
        self._draw_board()

    def _draw_board(self) -> None:
        """ Render the diagram on a new picture and immediately repaint the board. """
        gfx = self._gfx = QPicture()
        with QPainter(gfx) as p:
            # Set anti-aliasing on for best quality.
            p.setRenderHints(QPainter.Antialiasing)
            bounds = self._get_draw_bounds()
            self._renderer.render(p, bounds)
        self.update()

    def _get_draw_bounds(self) -> QRectF:
        """ Return the bounding box needed to center everything in the widget at maximum scale. """
        width = self.width()
        height = self.height()
        _, _, vw, vh = self._renderer.viewBoxF().getRect()
        if vw and vh:
            scale = min(width / vw, height / vh)
            fw, fh = vw * scale, vh * scale
            ox = (width - fw) / 2
            oy = (height - fh) / 2
            return QRectF(ox, oy, fw, fh)
        else:
            # If no valid viewbox is defined, use the widget's natural size.
            return QRectF(0, 0, width, height)

    def paintEvent(self, *args) -> None:
        """ Paint the saved board picture on this widget when GUI repaint occurs. """
        self._gfx.play(QPainter(self))

    def resizeEvent(self, *args) -> None:
        """ Reposition the link, redraw the board, and send the new widget aspect ratio on any size change. """
        width, height = self.width(), self.height()
        self._w_link.move(width - 75, height - 18)
        self._draw_board()
        self.sig_new_ratio.emit(width / height)

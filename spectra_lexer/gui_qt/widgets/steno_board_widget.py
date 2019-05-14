from PyQt5.QtCore import pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QPicture
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QLabel, QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _w_link: QLabel              # Displays rule hyperlink.
    _gfx: QPicture = QPicture()  # Last recorded rendering of the steno board.

    def __init__(self, *args):
        super().__init__(*args)
        self._w_link = QLabel("<a href='dummy'>More Examples</a>", self)
        self._w_link.setVisible(False)
        self._w_link.linkActivated.connect(lambda *args: self.onActivateLink.emit())

    def set_link(self, link_ref:str) -> None:
        """ Show a link in the bottom-right corner of the diagram if examples exist. """
        self._w_link.setVisible(bool(link_ref))

    def set_board(self, xml_data:bytes) -> None:
        """ Make a renderer to use the raw XML data with the available elements to draw.
            Render the diagram on the new picture graphic and immediately repaint the board. """
        renderer = QSvgRenderer(xml_data)
        bounds = self._get_draw_bounds(renderer.viewBoxF())
        gfx = QPicture()
        with QPainter(gfx) as p:
            # Set anti-aliasing on for best quality.
            p.setRenderHints(QPainter.Antialiasing)
            renderer.render(p, bounds)
        self._gfx = gfx
        self.update()

    def _get_draw_bounds(self, viewbox:QRectF) -> QRectF:
        """ Return the bounding box needed to center everything in the widget at maximum scale. """
        _, _, vw, vh = viewbox.getRect()
        width, height = self.width(), self.height()
        scale = min(width / vw, height / vh)
        fw, fh = vw * scale, vh * scale
        ox = (width - fw) / 2
        oy = (height - fh) / 2
        return QRectF(ox, oy, fw, fh)

    def paintEvent(self, *args) -> None:
        """ Paint the current set of elements on this widget when GUI repaint occurs. """
        self._gfx.play(QPainter(self))

    def resizeEvent(self, *args) -> None:
        """ Reposition the link and send the new widget dimensions on any size change. """
        width, height = self.width(), self.height()
        self._w_link.move(width - 75, height - 18)
        self.onResize.emit(width, height)

    # Signals
    onActivateLink = pyqtSignal()
    onResize = pyqtSignal([int, int])

from PyQt5.QtCore import QBuffer, QIODevice, QRectF
from PyQt5.QtGui import QColor, QImage, QPainter
from PyQt5.QtSvg import QSvgRenderer


class SVGRasterizer:
    """ Renders SVG data to raster images. """

    def __init__(self, w_max:int, h_max:int, *, bg_color=QColor(0, 0, 0, 0)) -> None:
        self._w_max = w_max        # Limit on image width in pixels.
        self._h_max = h_max        # Limit on image height in pixels.
        self._bg_color = bg_color  # Color to use for raster backgrounds.

    def encode(self, svg_data:str, fmt="PNG") -> bytes:
        """ Create a new bitmap image with the current background color and render an SVG image to it.
            Pixel dimensions will fit the viewbox at maximum scale.
            Convert the image to a data stream and return the raw bytes. """
        svg = QSvgRenderer(svg_data.encode("utf8"))
        v_size = svg.viewBox().size()
        vw = v_size.width()
        vh = v_size.height()
        scale = min(self._w_max / vw, self._h_max / vh)
        w = round(vw * scale)
        h = round(vh * scale)
        im = QImage(w, h, QImage.Format_ARGB32)
        im.fill(self._bg_color)
        with QPainter(im) as p:
            p.setRenderHints(QPainter.Antialiasing)
            svg.render(p, QRectF(0, 0, w, h))
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, fmt)
        return buf.data()

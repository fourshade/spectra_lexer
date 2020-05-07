""" Module for SVG operations using QtSvg. """

from PyQt5.QtCore import QRectF, QIODevice, QBuffer
from PyQt5.QtGui import QColor, QImage, QPainter, QPicture
from PyQt5.QtSvg import QSvgRenderer


class SVGConverter:
    """ Converts SVG images to raster formats. """

    def __init__(self, *, background_rgba=(255, 255, 255, 0)) -> None:
        self._bg_color = QColor(*background_rgba)  # Color to use for background from RGBA 0-255 format.

    def to_png(self, svg_data:bytes) -> bytes:
        """ Render SVG bytes on a transparent bitmap image and convert it to a PNG stream.
            Use the viewbox dimensions as pixel sizes. """
        svg = QSvgRenderer(svg_data)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self._bg_color)
        with QPainter(im) as p:
            svg.render(p)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, "PNG")
        return buf.data()


class SVGPictureRenderer:
    """ Renders SVG bytes data on QPictures. """

    def __init__(self, *, render_hints=QPainter.Antialiasing) -> None:
        self._renderer = QSvgRenderer()    # XML SVG renderer.
        self._render_hints = render_hints  # SVG rendering quality hints (such as anti-aliasing).

    def set_data(self, svg_data:bytes) -> None:
        """ Load the renderer with raw XML data containing the SVG elements to draw. """
        self._renderer.load(svg_data)

    def render_fit(self, width:float, height:float) -> QPicture:
        """ Render the current SVG elements on a new picture of size <width, height> and return it. """
        gfx = QPicture()
        with QPainter(gfx) as p:
            p.setRenderHints(self._render_hints)
            bounds = self._fit_bounds(width, height)
            self._renderer.render(p, bounds)
        return gfx

    def _fit_bounds(self, width:float, height:float) -> QRectF:
        """ Return the bounding box needed to center everything in the picture at maximum scale. """
        _, _, vw, vh = self._renderer.viewBoxF().getRect()
        if vw and vh:
            scale = min(width / vw, height / vh)
            fw, fh = vw * scale, vh * scale
            ox = (width - fw) / 2
            oy = (height - fh) / 2
            return QRectF(ox, oy, fw, fh)
        else:
            # If no valid viewbox is defined, use the given size directly.
            return QRectF(0, 0, width, height)

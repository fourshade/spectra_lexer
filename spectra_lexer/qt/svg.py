""" Wrappers for the Qt SVG renderer. """

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QColor, QIcon, QImage, QPainter, QPicture, QPixmap
from PyQt5.QtSvg import QSvgRenderer


class SVGIconRenderer:
    """ Renders SVG bytes data on bitmap images to create QIcons and caches the results. """

    # Icons are small but important. Use these render hints by default for best quality.
    _HQ_RENDER_HINTS = QPainter.Antialiasing | QPainter.SmoothPixmapTransform

    def __init__(self, bg_color=QColor(255, 255, 255, 0), *, render_hints=_HQ_RENDER_HINTS) -> None:
        self._bg_color = bg_color          # Background color for icons (transparent white by default).
        self._render_hints = render_hints  # Render quality hints for the SVG painter/renderer.
        self._cache = {}                   # Cache of icons already rendered, keyed by the XML that generated it.

    def render(self, xml:bytes) -> QIcon:
        """ If we have the XML rendered, return the icon from the cache. Otherwise, render and cache it first. """
        if xml not in self._cache:
            self._cache[xml] = self._render(xml)
        return self._cache[xml]

    def _render(self, xml:bytes) -> QIcon:
        """ Create a template image, render the XML in place, and convert it to an icon.
            Use the viewbox dimensions as pixel sizes. """
        svg = QSvgRenderer(xml)
        viewbox = svg.viewBox().size()
        im = QImage(viewbox, QImage.Format_ARGB32)
        im.fill(self._bg_color)
        with QPainter(im) as p:
            p.setRenderHints(self._render_hints)
            svg.render(p)
        return QIcon(QPixmap.fromImage(im))


class SVGPictureRenderer:
    """ Renders SVG bytes data on QPictures. """

    def __init__(self, *, render_hints=QPainter.Antialiasing) -> None:
        self._renderer = QSvgRenderer()    # XML SVG renderer.
        self._render_hints = render_hints  # SVG rendering quality hints (such as anti-aliasing).

    def set_data(self, xml_data=b"") -> None:
        """ Load the renderer with raw XML data containing the SVG elements to draw. """
        self._renderer.load(xml_data)

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

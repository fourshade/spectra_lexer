""" Module for SVG operations using QtSvg. """

from typing import Tuple, Union

from PyQt5.QtCore import QRectF, QIODevice, QBuffer
from PyQt5.QtGui import QColor, QImage, QPainter, QPaintDevice
from PyQt5.QtSvg import QSvgRenderer

QtSVGData = Union[bytes, str]  # Valid formats for an SVG data string. The XML header is not required.


class SVGEngine:
    """ Renders SVG bytes data on QPictures. """

    def __init__(self, *, render_hints=QPainter.Antialiasing, background_rgba=(255, 255, 255, 255)) -> None:
        self._data = b""                         # Current XML SVG binary data.
        self._renderer = QSvgRenderer()          # Qt SVG renderer.
        self._render_hints = render_hints        # SVG rendering quality hints (such as anti-aliasing).
        self._background_rgba = background_rgba  # Color to use for raster backgrounds in RGBA 0-255 format.

    def load(self, data:QtSVGData) -> None:
        """ Load the renderer with XML data containing the SVG elements to draw. """
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._data = data
        self._renderer.load(data)

    def _viewbox_size(self) -> Tuple[float, float]:
        v_rect = self._renderer.viewBoxF()
        return v_rect.width(), v_rect.height()

    def best_fit(self, width:float, height:float) -> QRectF:
        """ Return the bounding box needed to center everything in a rectangle of <width, height> at maximum scale. """
        vw, vh = self._viewbox_size()
        if vw and vh:
            scale = min(width / vw, height / vh)
            fw, fh = vw * scale, vh * scale
            ox = (width - fw) / 2
            oy = (height - fh) / 2
            return QRectF(ox, oy, fw, fh)
        else:
            # If no valid viewbox is defined, just return the full rectangle.
            return QRectF(0, 0, width, height)

    def render(self, target:QPaintDevice, *args:QRectF) -> None:
        """ Render the current SVG data on <target> with an optional QRectF bounding box. """
        with QPainter(target) as p:
            p.setRenderHints(self._render_hints)
            self._renderer.render(p, *args)

    def _make_image(self) -> QImage:
        """ Render the current SVG data on a new bitmap image. Use the viewbox dimensions as pixel sizes. """
        vw, vh = self._viewbox_size()
        im = QImage(int(vw), int(vh), QImage.Format_ARGB32)
        bg_color = QColor(*self._background_rgba)
        im.fill(bg_color)
        self.render(im)
        return im

    def make_png(self) -> bytes:
        """ Render SVG character data as a raster image and convert it to a PNG stream. """
        im = self._make_image()
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, "PNG")
        return buf.data()

    def save(self, filename:str) -> None:
        """ Save the current SVG data directly to disk. """
        with open(filename, 'wb') as fp:
            fp.write(self._data)

    def save_png(self, filename:str) -> None:
        """ Save the current SVG data as a PNG file. """
        png_data = self.make_png()
        with open(filename, 'wb') as fp:
            fp.write(png_data)

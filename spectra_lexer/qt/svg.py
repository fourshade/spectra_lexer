""" Module for SVG operations using QtSvg. """

from typing import Union

from PyQt5.QtCore import QBuffer, QIODevice, QRectF, QSize
from PyQt5.QtGui import QColor, QImage, QPaintDevice, QPainter
from PyQt5.QtSvg import QSvgRenderer

QtSVGData = Union[bytes, str]  # Valid formats for an SVG data string. The XML header is not required.


class SVGEngine:
    """ Renders SVG data on Qt paint devices and/or raster images. """

    def __init__(self, *, render_hints=QPainter.Antialiasing, background_rgba=(255, 255, 255, 255)) -> None:
        self._data = b""                         # Current XML SVG binary data.
        self._renderer = QSvgRenderer()          # Qt SVG renderer.
        self._render_hints = render_hints        # SVG rendering quality hints (such as anti-aliasing).
        self._background_rgba = background_rgba  # Color to use for raster backgrounds in RGBA 0-255 format.

    def loads(self, data:QtSVGData) -> None:
        """ Load the renderer with SVG data. """
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._data = data
        self._renderer.load(data)

    def load(self, filename:str) -> None:
        """ Load SVG data directly from disk. """
        with open(filename) as fp:
            data = fp.read()
        self.loads(data)

    def dumps(self) -> str:
        """ Return the current SVG data as a string. """
        return self._data.decode('utf-8')

    def dump(self, filename:str) -> None:
        """ Save the current SVG data directly to disk. """
        with open(filename, 'wb') as fp:
            fp.write(self._data)

    def viewbox_size(self) -> QSize:
        """ If no valid viewbox is defined, 100x100 is a typical default. """
        size = self._renderer.viewBox().size()
        if size.isEmpty():
            size = QSize(100, 100)
        return size

    def render(self, target:QPaintDevice, bounds:QRectF) -> None:
        """ Render the current SVG data on <target>, scaled to fit inside <bounds>. """
        with QPainter(target) as p:
            p.setRenderHints(self._render_hints)
            self._renderer.render(p, bounds)

    def render_fit(self, target:QPaintDevice) -> None:
        """ Render the current SVG data on <target>, centered at maximum scale while preserving aspect ratio. """
        width = target.width()
        height = target.height()
        v_size = self.viewbox_size()
        vw = v_size.width()
        vh = v_size.height()
        scale = min(width / vw, height / vh)
        rw = vw * scale
        rh = vh * scale
        rx = (width - rw) / 2
        ry = (height - rh) / 2
        bounds = QRectF(rx, ry, rw, rh)
        self.render(target, bounds)

    def draw_image(self, size:QSize=None) -> QImage:
        """ Create a new bitmap image of <size> with the current background color and render the SVG data to it.
            If <size> is None, treat the viewbox as pixel dimensions. """
        if size is None:
            size = self.viewbox_size()
        im = QImage(size, QImage.Format_ARGB32)
        bg_color = QColor(*self._background_rgba)
        im.fill(bg_color)
        self.render_fit(im)
        return im

    def encode_image(self, size:QSize=None, *, fmt="PNG") -> bytes:
        """ Render to a bitmap image and convert it to a data stream. """
        im = self.draw_image(size)
        buf = QBuffer()
        buf.open(QIODevice.WriteOnly)
        im.save(buf, fmt)
        return buf.data()

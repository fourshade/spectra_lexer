""" Module for SVG operations using QtSvg. """

from typing import Union

from PyQt5.QtCore import QRectF, QSize
from PyQt5.QtGui import QPaintDevice, QPainter
from PyQt5.QtSvg import QSvgRenderer

QtSVGData = Union[bytes, str]  # Valid formats for an SVG data string. The XML header is not required.


class SVGEngine:
    """ Renders SVG data on Qt paint devices. """

    def __init__(self, *, render_hints=QPainter.Antialiasing) -> None:
        self._data = b""                   # Current XML SVG binary data.
        self._renderer = QSvgRenderer()    # Qt SVG renderer.
        self._render_hints = render_hints  # SVG rendering quality hints (such as anti-aliasing).

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

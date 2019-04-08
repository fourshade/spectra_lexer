from functools import lru_cache
from typing import Callable, Dict, Iterable, List

from PyQt5.QtCore import QRectF, QXmlStreamReader
from PyQt5.QtGui import QColor, QIcon, QImage, QPainter, QPaintDevice, QPixmap
from PyQt5.QtSvg import QSvgRenderer


class _SvgRenderer(QSvgRenderer):
    """ SVG renderer with simple helper methods. """

    def load_str(self, xml_string:str) -> None:
        """ Load all SVG elements from an SVG XML string. """
        self.load(QXmlStreamReader(xml_string))

    def viewbox_tuple(self) -> tuple:
        """ Return a tuple of (x, y, w, h) ints representing the viewbox bounds. """
        return self.viewBox().getRect()


class IconRenderer(_SvgRenderer):
    """ SVG renderer that renders static icons on transparent bitmap images and returns these when called. """

    _RENDER_HINTS = QPainter.Antialiasing | QPainter.SmoothPixmapTransform  # Icons are small; render in best quality.

    _blank: QImage      # Transparent template image.
    _ifinder: Callable  # Finds a valid icon element ID corresponding to an object.

    def __init__(self, xml_string:str, ifinder:Callable):
        """ Load an SVG XML string and create a blank template image with the viewbox dimensions. """
        super().__init__()
        self.load_str(xml_string)
        self._blank = QImage(*self.viewbox_tuple()[2:], QImage.Format_ARGB32)
        self._blank.fill(QColor.fromRgb(255, 255, 255, 0))
        self._ifinder = ifinder

    def __call__(self, obj:object) -> QIcon:
        """ Return a cached copy of the required icon, or if it doesn't exist yet, draw it. """
        return self._get_icon(self._ifinder(obj))

    @lru_cache(maxsize=None)
    def _get_icon(self, k:str) -> QIcon:
        """ Make a copy of the template, draw the SVG element on it, convert it to an icon, and cache it. """
        im = QImage(self._blank)
        p = QPainter(im)
        p.setRenderHints(self._RENDER_HINTS)
        self.render(p, k, self.boundsOnElement(k))
        p.end()
        return QIcon(QPixmap.fromImage(im))


class LayoutRenderer(_SvgRenderer):
    """ SVG renderer that tracks the bounds of all elements with IDs and draws them individually with offsets. """

    _bounds: Dict[str, tuple] = {}  # (x, y, w, h) bounds of each graphical element by id.
    _draw_list: List[tuple] = []    # List of graphical element IDs with bounds rects.

    def load_ids(self, ids:Iterable[str]) -> None:
        """ Compute and store a dict of bounds for all given element IDs. """
        self._bounds = {k: self.boundsOnElement(k).getRect() for k in ids}

    def set_elements(self, element_info:Iterable[tuple]) -> None:
        """ Load the draw list with new elements after scaling and offsetting their bounds. """
        self._draw_list = dlist = []
        bounds = self._bounds
        for (e_id, ox, oy, scale) in element_info:
            if e_id in bounds:
                x, y, w, h = [c * scale for c in bounds[e_id]]
                rectf = QRectF(x + ox, y + oy, w, h)
                dlist.append((e_id, rectf))

    def paint(self, target:QPaintDevice) -> None:
        """ Paint the current element set on the given device. Undefined elements are simply ignored. """
        p = QPainter(target)
        render = self.render
        for (e_id, rectf) in self._draw_list:
            render(p, e_id, rectf)

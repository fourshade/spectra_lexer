from typing import Dict

from PyQt5.QtCore import QXmlStreamReader
from PyQt5.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


class IconRenderer(QSvgRenderer):

    _blank: QImage  # Transparent prototype image.
    _saved: list    # List of references to keep to avoid crashing.

    def __init__(self, xml_string:str):
        """ Load all SVG elements from an SVG XML string and create the starting image. """
        super().__init__(QXmlStreamReader(xml_string))
        x, y, w, h = self.viewBox().getRect()
        self._blank = QImage(w, h, QImage.Format_ARGB32)
        self._blank.fill(QColor.fromRgb(255, 255, 255, 0))
        self._saved = [self._blank]

    def draw(self, k:str) -> QIcon:
        im = QImage(self._blank)
        self._saved.append(im)
        self.render(QPainter(im), k, self.boundsOnElement(k))
        return QIcon(QPixmap.fromImage(im))


class IconFinder:

    _icons: Dict[str, QIcon]

    def __init__(self, d:dict):
        """ Load the dict with all icon graphics from an SVG XML string. """
        icons = self._icons = {}
        gfx = IconRenderer(d["raw"])
        # Each element ID without a starting underline is a valid icon.
        # The types it corresponds to are separated by + characters.
        for k in d["id"]:
            if not k.startswith("_"):
                icon = gfx.draw(k)
                for tp in k.split("+"):
                    icons[tp] = icon

    def get_icon(self, obj:object) -> QIcon:
        """ Return the icon for this object's type or its closest ancestor. """
        _get = self._icons.get
        for tp in type(obj).__mro__:
            icon = _get(tp.__name__)
            if icon is not None:
                return icon

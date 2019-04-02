from typing import Dict

from PyQt5.QtCore import QXmlStreamReader
from PyQt5.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


class IconFinder(Dict[str, QIcon]):

    def __init__(self, d:dict):
        """ Load all icon graphics from an SVG XML string. """
        super().__init__()
        gfx = QSvgRenderer(QXmlStreamReader(d["raw"]))
        x, y, w, h = gfx.viewBox().getRect()
        bg = QColor.fromRgb(255, 255, 255, 0)
        saved = self[""] = []
        # Each element ID without a starting underline is a valid icon.
        # The types it corresponds to are separated by underlines.
        ids = [k for k in d["id"] if not k.startswith("_")]
        for k in ids:
            im = QImage(w, h, QImage.Format_ARGB32)
            im.fill(bg)
            saved += [im]
            bounds = gfx.boundsOnElement(k)
            gfx.render(QPainter(im), k, bounds)
            icon = QIcon(QPixmap.fromImage(im))
            for tp in k.split("_"):
                self[tp] = icon

    def __missing__(self, k:str) -> QIcon:
        return self["default"]

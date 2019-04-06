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
        """ Create a copy of the blank reference image. Save its reference so Qt doesn't delete it while drawing. """
        im = QImage(self._blank)
        self._saved.append(im)
        self.render(QPainter(im), k, self.boundsOnElement(k))
        return QIcon(QPixmap.fromImage(im))


class IconFinder(dict):

    def __init__(self, d:dict):
        """ Load the dict with all icon graphics by name from an SVG XML string. """
        super().__init__()
        gfx = IconRenderer(d["raw"])
        # Each element ID without a starting underline is a valid icon.
        # The types it corresponds to are separated by + characters.
        for k in d["id"]:
            if not k.startswith("_"):
                icon = gfx.draw(k)
                for tp_name in k.split("+"):
                    self[tp_name] = icon

    def get_icon(self, obj:object) -> QIcon:
        """ Return the closest icon to this object's type. Search the MRO by both type and name if none is found.
            Once a match is found (`object` must always match), save it under each type traversed. """
        tp = type(obj)
        if tp in self:
            return self[tp]
        for i, cls in enumerate(tp.__mro__):
            icon = self.get(cls) or self.get(cls.__name__)
            if icon is not None:
                self.update(dict.fromkeys(tp.__mro__[:i+1], icon))
                return icon

from typing import Dict, Iterable, List

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QColor, QPainter, QIcon, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from spectra_lexer.utils import memoize


class IconRenderer(dict):
    """ SVG icon dict that renders static icons on transparent bitmap images. """

    def __init__(self, xml_bytes:bytes, icon_ids:Dict[str, list]):
        """ Load an SVG XML string and create a blank template image with the viewbox size. """
        super().__init__()
        gfx = QSvgRenderer(xml_bytes)
        blank = QImage(gfx.viewBox().size(), QImage.Format_ARGB32)
        blank.fill(QColor.fromRgb(255, 255, 255, 0))
        # Create an icon dict using the SVG element IDs and their aliases.
        for k, names in icon_ids.items():
            # For each SVG element, copy the template, render the element in place, and convert it to an icon.
            im = QImage(blank)
            with QPainter(im) as p:
                # Icons are small but important; set render hints for every new painter to render in best quality.
                p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
                gfx.render(p, k, gfx.boundsOnElement(k))
            icon = QIcon(QPixmap.fromImage(im))
            for n in names:
                self[n] = icon

    def __call__(self, choices:Iterable[str]) -> QIcon:
        """ Return an available icon from a sequence of choices from most wanted to least. """
        return next(filter(None, map(self.get, choices)), None)


class ItemFormatter:

    _FLAGS = Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Default item flags. Items are black and selectable.
    _role_map: List[tuple]  # Maps string keys to Qt roles, with a formatting function applied to the data.

    def __init__(self, **kwargs):
        """ Create the role data map with the [caching] color generator and icon finder. """
        self._role_map = [("text",         Qt.DisplayRole,    lambda x: x),
                          ("tooltip",      Qt.ToolTipRole,    lambda x: x),
                          ("icon_choices", Qt.DecorationRole, IconRenderer(**kwargs)),
                          ("color",        Qt.ForegroundRole, memoize(lambda t: QColor(*t)))]

    def __call__(self, data:dict):
        """ Assign the parent, item flags, and various pieces of data in string keys to Qt roles for item display. """
        data.update({r: f(data[k]) for k, r, f in self._role_map if k in data}, flags=Qt.ItemFlags(self._FLAGS))
        if data.get("edit"):
            data["flags"] |= Qt.ItemIsEditable
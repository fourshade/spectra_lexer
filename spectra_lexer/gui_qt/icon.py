from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon, QImage, QColor, QPainter, QPixmap
from PyQt5.QtSvg import QSvgRenderer


class IconRenderer(QSvgRenderer):
    """ SVG renderer for static icons on transparent bitmap images. """

    def generate(self, size:QSize=None) -> QIcon:
        """ Create a blank template, render the element in place, and convert it to an icon.
            If no size is given, use the viewbox dimensions as pixel sizes. """
        im = QImage(size or self.viewBox().size(), QImage.Format_ARGB32)
        im.fill(QColor.fromRgb(255, 255, 255, 0))
        with QPainter(im) as p:
            # Icons are small but important; set render hints for best quality.
            p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
            self.render(p)
        return QIcon(QPixmap.fromImage(im))

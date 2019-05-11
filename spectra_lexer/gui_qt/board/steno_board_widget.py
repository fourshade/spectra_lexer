from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QPainter, QPicture
from PyQt5.QtWidgets import QLabel, QWidget


class StenoBoardWidget(QWidget):
    """ Widget to display all the keys that make up a steno stroke pictorally. """

    _w_link: QLabel              # Displays rule hyperlink.
    _gfx: QPicture = QPicture()  # Last recorded rendering of the steno board.

    def __init__(self, *args):
        super().__init__(*args)
        self._w_link = QLabel("<a href='dummy'>More Examples</a>", self)
        self._w_link.setVisible(False)
        self._w_link.linkActivated.connect(lambda *args: self.onActivateLink.emit())

    def set_link_enabled(self, enabled:bool) -> None:
        """ Show a link in the bottom-right corner of the diagram if examples exist. """
        self._w_link.setVisible(enabled)

    def set_gfx(self, gfx:QPicture) -> None:
        """ Set the new picture graphic and immediately repaint the board. """
        self._gfx = gfx
        self.update()

    def paintEvent(self, *args) -> None:
        """ Paint the current set of elements on this widget when GUI repaint occurs. """
        self._gfx.play(QPainter(self))

    def resizeEvent(self, *args) -> None:
        """ Reposition the link and send the new widget dimensions on any size change. """
        self._w_link.move(self.width() - 75, self.height() - 18)
        self.onResize.emit(self.width(), self.height())

    # Signals
    onActivateLink = pyqtSignal()
    onResize = pyqtSignal([int, int])

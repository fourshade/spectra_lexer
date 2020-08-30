from typing import Callable

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, QContextMenuEvent, QGuiApplication, QImage, QPaintDevice, QPainter, QPixmap
from PyQt5.QtWidgets import QLabel, QMenu, QSlider, QWidget

from .svg import QtSVGData, SVGEngine

LinkCallback = Callable[[], None]


class Clipboard:
    """ Wrapper for system clipboard operations. """

    def __init__(self) -> None:
        self._qclipboard = QGuiApplication.clipboard()  # System clipboard singleton.

    def copy(self, obj:object) -> None:
        """ Copy an object to the clipboard. """
        if isinstance(obj, str):
            self._qclipboard.setText(obj)
        elif isinstance(obj, QImage):
            self._qclipboard.setImage(obj)
        elif isinstance(obj, QPixmap):
            self._qclipboard.setPixmap(obj)
        else:
            raise TypeError("Object type is not supported by the clipboard.")


class BoardWidget(QWidget):
    """ SVG-based widget with a manual paint buffer. """

    PAINT_BG = QColor(0, 0, 0, 0)         # Transparent background for widget painting.
    COPY_BG = QColor(255, 255, 255, 255)  # White background for the clipboard.

    resized = pyqtSignal()

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._svg = SVGEngine()        # SVG rendering engine.
        self._clipboard = Clipboard()  # System clipboard wrapper.
        self._pixmap = QPixmap()       # Last saved rendering.
        self._ctx_menu = QMenu(self)   # Context menu to copy diagram to clipboard.
        self._ctx_menu_on = False
        self._ctx_menu.addAction("Copy Image", self.copyImage)

    def _paint_to(self, target:QPaintDevice) -> None:
        """ Paint the saved rendering to <target>. """
        with QPainter(target) as p:
            p.drawPixmap(0, 0, self._pixmap)

    def _render(self) -> None:
        """ Render the diagram based on the current size and repaint the widget. """
        self._pixmap = pixmap = QPixmap(self.size())
        pixmap.fill(self.PAINT_BG)
        self._svg.render_fit(pixmap)
        self.update()

    def setSvgData(self, data:QtSVGData) -> None:
        """ Set new SVG image data and render it. """
        self._svg.loads(data)
        self._ctx_menu_on = bool(data)
        self._render()

    def copyImage(self) -> None:
        """ Copy the current rendering to the clipboard with a solid background. """
        pcopy = QPixmap(self._pixmap.size())
        pcopy.fill(self.COPY_BG)
        self._paint_to(pcopy)
        self._clipboard.copy(pcopy)

    def saveImage(self, filename:str) -> None:
        """ Save the current rendering to an image file. Format is determined by the file extension. """
        ext = filename[-3:]
        if ext.lower() == 'svg':
            self._svg.dump(filename)
        else:
            self._pixmap.save(filename, ext)

    def paintEvent(self, _) -> None:
        """ Repaint the widget with the saved rendering. """
        self._paint_to(self)

    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        """ Send a signal on a context menu request (right-click). """
        if self._ctx_menu_on:
            pos = event.globalPos()
            self._ctx_menu.popup(pos)

    def resizeEvent(self, _) -> None:
        """ Rerender on any widget size change and send a signal. """
        self._render()
        self.resized.emit()


class BoardPanel:
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    def __init__(self, w_board:BoardWidget, w_caption:QLabel, w_slider:QSlider,
                 w_link_save:QLabel, w_link_examples:QLabel) -> None:
        self._w_board = w_board                  # Board diagram container widget.
        self._w_caption = w_caption              # Label with caption containing rule keys/letters/description.
        self._w_slider = w_slider                # Slider to control board rendering options.
        self._w_link_save = w_link_save          # Hyperlink to save diagram as file.
        self._w_link_examples = w_link_examples  # Hyperlink to show examples of the current rule.

    def connect_signals(self, call_invalid:LinkCallback, call_save:LinkCallback,
                        call_examples:LinkCallback, *, dynamic_resize=True) -> None:
        """ Connect Qt signals (none of their arguments are used). """
        # Invalidate the board on any size change (expensive, only if dynamic_resize=True)
        if dynamic_resize:
            self._w_board.resized.connect(call_invalid)
        # On slider movements, declare the board invalid to get new data.
        self._w_slider.valueChanged.connect(lambda *_: call_invalid())
        # Save the current diagram on link click.
        self._w_link_save.linkActivated.connect(lambda *_: call_save())
        # Start an example search for the current rule on link click.
        self._w_link_examples.linkActivated.connect(lambda *_: call_examples())

    def aspect_ratio(self) -> float:
        """ Return the width / height aspect ratio of the board widget. """
        size = self._w_board.size()
        return size.width() / size.height()

    def is_compound(self) -> bool:
        """ The board is compound if not in keys mode (slider at top, value=0). """
        return self._w_slider.value() > 0

    def shows_letters(self) -> bool:
        """ The board uses letters only if in letters mode (slider at bottom, value=2). """
        return self._w_slider.value() > 1

    def set_enabled(self, enabled:bool) -> None:
        self._w_slider.setEnabled(enabled)

    def set_caption(self, caption:str) -> None:
        """ Show a new caption above the board diagram. """
        self._w_caption.setText(caption)

    def set_data(self, data:QtSVGData) -> None:
        """ Load the renderer with new SVG data and redraw the board. """
        self._w_board.setSvgData(data)
        self._w_link_save.setVisible(bool(data))

    def dump_image(self, filename:str) -> None:
        """ Save the current diagram to an SVG file (or other format). """
        self._w_board.saveImage(filename)

    def show_examples_link(self) -> None:
        """ Show the link in the bottom-right corner of the diagram. """
        self._w_link_examples.setVisible(True)

    def hide_examples_link(self) -> None:
        """ Hide the link in the bottom-right corner of the diagram. """
        self._w_link_examples.setVisible(False)

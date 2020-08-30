from typing import Callable

from PyQt5.QtCore import pyqtSignal, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QContextMenuEvent, QGuiApplication, QImage, QPainter, QPicture
from PyQt5.QtWidgets import QLabel, QMenu, QSlider, QWidget

from .svg import QtSVGData, SVGRasterEngine

LinkCallback = Callable[[], None]


class BoardWidget(QWidget):
    """ Widget using a QPicture as a paint buffer. """

    def __init__(self, *args) -> None:
        super().__init__(*args)
        self._picture = QPicture()  # Last saved picture rendering.

    def __enter__(self) -> QPicture:
        """ Reset the current picture, size it to match the widget, and return it for rendering. """
        self._picture = picture = QPicture()
        rect = QRect()
        rect.setSize(self.size())
        picture.setBoundingRect(rect)
        return picture

    def __exit__(self, *_) -> None:
        """ Repaint the widget after rendering is complete. """
        self.update()

    def paintEvent(self, *_) -> None:
        """ Paint the saved picture on this widget when GUI repaint occurs. """
        with QPainter(self) as p:
            self._picture.play(p)

    # should be inherited from a: """ Mixin to send a signal on a context menu request (right-click). """

    contextMenuRequest = pyqtSignal([QPoint])

    def contextMenuEvent(self, event:QContextMenuEvent) -> None:
        pos = event.globalPos()
        self.contextMenuRequest.emit(pos)

    # should be inherited from a: """ Mixin to send a signal on any widget size change. """

    resized = pyqtSignal()

    def resizeEvent(self, *_) -> None:
        self.resized.emit()


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
        else:
            raise TypeError("Object type is not supported by the clipboard.")


class BoardPanel:
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    def __init__(self, w_board:BoardWidget, w_caption:QLabel, w_slider:QSlider,
                 w_link_save:QLabel, w_link_examples:QLabel, *, dynamic_resize=True) -> None:
        self._w_board = w_board                  # Board diagram container widget.
        self._w_caption = w_caption              # Label with caption containing rule keys/letters/description.
        self._w_slider = w_slider                # Slider to control board rendering options.
        self._w_link_save = w_link_save          # Hyperlink to save diagram as file.
        self._w_link_examples = w_link_examples  # Hyperlink to show examples of the current rule.
        self._ctx_menu = QMenu(w_board)          # Context menu to copy diagram to clipboard.
        self._dynamic_resize = dynamic_resize    # If True, invalidate the board on resize to get new data.
        self._svg = SVGRasterEngine()            # SVG rendering engine.
        self._clipboard = Clipboard()            # System clipboard wrapper.
        self._call_invalid = None
        self._call_save = None
        self._call_examples = None

    def _get_size(self) -> QSize:
        """ Return the size of the board widget. """
        return self._w_board.size()

    def _draw_board(self) -> None:
        """ Render the diagram to the board widget. """
        with self._w_board as target:
            self._svg.render_fit(target)

    def _draw_image(self) -> QImage:
        """ Render the diagram to a bitmap image at the same size as is currently displayed. """
        w_size = self._get_size()
        im_size = self._svg.viewbox_size()
        im_size.scale(w_size, Qt.KeepAspectRatio)
        return self._svg.draw_image(im_size)

    def _on_copy(self, *_) -> None:
        """ Draw the board to a bitmap image and copy that to the clipboard. """
        im = self._draw_image()
        self._clipboard.copy(im)

    def _on_resize(self, *_) -> None:
        """ Redraw or invalidate the board on any size change. """
        if self._dynamic_resize:
            self._call_invalid()
        else:
            self._draw_board()

    def _on_slider_move(self, *_) -> None:
        """ On slider movements, declare the board invalid to get new data. """
        self._call_invalid()

    def _on_save_link_click(self, *_) -> None:
        """ Save the current diagram on link click. """
        self._call_save()

    def _on_examples_link_click(self, *_) -> None:
        """ Start an example search for the current rule on link click. """
        self._call_examples()

    def connect_signals(self, call_invalid:LinkCallback, call_save:LinkCallback, call_examples:LinkCallback) -> None:
        """ Connect Qt signals and set callback functions. """
        self._call_invalid = call_invalid
        self._call_save = call_save
        self._call_examples = call_examples
        self._ctx_menu.addAction("Copy Image", self._on_copy)
        self._w_board.contextMenuRequest.connect(self._ctx_menu.popup)
        self._w_board.resized.connect(self._on_resize)
        self._w_slider.valueChanged.connect(self._on_slider_move)
        self._w_link_save.linkActivated.connect(self._on_save_link_click)
        self._w_link_examples.linkActivated.connect(self._on_examples_link_click)

    def aspect_ratio(self) -> float:
        """ Return the width / height aspect ratio of the board widget. """
        size = self._get_size()
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
        self._svg.loads(data)
        self._ctx_menu.setEnabled(bool(data))
        self._w_link_save.setVisible(bool(data))
        self._draw_board()

    def dump_image(self, filename:str) -> None:
        """ Save the current diagram to an SVG file (or other format). """
        ext = filename[-3:]
        if ext == 'svg':
            self._svg.dump(filename)
        else:
            im = self._draw_image()
            im.save(filename, ext)

    def show_examples_link(self) -> None:
        """ Show the link in the bottom-right corner of the diagram. """
        self._w_link_examples.setVisible(True)

    def hide_examples_link(self) -> None:
        """ Hide the link in the bottom-right corner of the diagram. """
        self._w_link_examples.setVisible(False)

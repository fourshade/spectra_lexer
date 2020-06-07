from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QGuiApplication, QImage
from PyQt5.QtWidgets import QLabel, QMenu

from .file import save_file_dialog
from .svg import QtSVGData, SVGRasterEngine
from .widgets import PictureWidget


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


class DisplayBoard:
    """ Displays all of the keys that make up one or more steno strokes pictorally. """

    def __init__(self, w_board:PictureWidget, w_link_save:QLabel) -> None:
        self._w_board = w_board          # Board diagram container widget.
        self._w_link_save = w_link_save  # Hyperlink to save diagram as file.
        self._ctx_menu = QMenu(w_board)  # Context menu to copy diagram to clipboard.
        self._svg = SVGRasterEngine()    # SVG rendering engine.
        self._clipboard = Clipboard()    # System clipboard wrapper.

    def get_size(self) -> QSize:
        """ Return the size of the board widget. """
        return self._w_board.size()

    def _draw_board(self) -> None:
        """ Render the diagram to the board widget. """
        with self._w_board as target:
            self._svg.render_fit(target)

    def _draw_image(self) -> QImage:
        """ Render the diagram to a bitmap image at the same size as is currently displayed. """
        w_size = self.get_size()
        im_size = self._svg.viewbox_size()
        im_size.scale(w_size, Qt.KeepAspectRatio)
        return self._svg.draw_image(im_size)

    def _on_copy(self, *_) -> None:
        """ Draw the board to a bitmap image and copy that to the clipboard. """
        im = self._draw_image()
        self._clipboard.copy(im)

    def _on_resize(self, *_) -> None:
        """ Redraw the board on any size change. """
        self._draw_board()

    def _on_link_click(self, *_) -> None:
        """ Save the current diagram to an SVG file (or other format) on link click. """
        filename = save_file_dialog(self._w_board, "Save File", "svg|png", "board.svg")
        if filename:
            ext = filename[-3:]
            if ext == 'svg':
                self._svg.dump(filename)
            else:
                im = self._draw_image()
                im.save(filename, ext)

    def connect_signals(self) -> None:
        """ Connect Qt signals and set callback functions. """
        self._ctx_menu.addAction("Copy Image", self._on_copy)
        self._w_board.contextMenuRequest.connect(self._ctx_menu.popup)
        self._w_board.resized.connect(self._on_resize)
        self._w_link_save.linkActivated.connect(self._on_link_click)

    def set_data(self, data:QtSVGData) -> None:
        """ Load the renderer with new SVG data and redraw the board. """
        self._svg.loads(data)
        self._ctx_menu.setEnabled(bool(data))
        self._w_link_save.setVisible(bool(data))
        self._draw_board()

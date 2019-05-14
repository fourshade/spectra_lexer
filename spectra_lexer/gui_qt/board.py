from functools import partial

from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPainter, QPicture
from PyQt5.QtSvg import QSvgRenderer

from .window import GUI
from spectra_lexer.core import COREApp, Component, Signal
from spectra_lexer.view import VIEWBoard, VIEWSearch


class GUIQTBoard:

    class Link:
        @Signal
        def on_example_link(self) -> None:
            raise NotImplementedError


class QtBoard(Component, GUIQTBoard,
              GUI.DisplayBoard, GUI.DisplayDescription,
              COREApp.Start, VIEWSearch.NewInfo, VIEWBoard.NewDiagram):
    """ Draws steno board diagram elements and the description for rules. """

    def on_app_start(self) -> None:
        """ Connect the signals and initialize the board size. """
        self.w_board.onActivateLink.connect(partial(self.engine_call, self.Link))
        self.w_board.onResize.connect(partial(self.engine_call, VIEWBoard.resize))
        self.w_board.resizeEvent()

    def on_view_info(self, caption:str, link_ref:str) -> None:
        """ Show a caption above the board and optionally a link in the bottom-right corner. """
        self.w_desc.setText(caption)
        self.w_board.set_link_enabled(bool(link_ref))

    def on_view_board_diagram(self, xml_data:bytes) -> None:
        """ Make a renderer to use the raw XML data with the available elements to draw.
            Render the diagram and send the finished picture to the board widget. """
        renderer = QSvgRenderer(xml_data)
        bounds = self._get_draw_bounds(renderer.viewBoxF())
        gfx = QPicture()
        with QPainter(gfx) as p:
            # Set anti-aliasing on for best quality.
            p.setRenderHints(QPainter.Antialiasing)
            renderer.render(p, bounds)
        self.w_board.set_gfx(gfx)

    def _get_draw_bounds(self, viewbox:QRectF) -> QRectF:
        """ Return the bounding box needed to center everything in the widget at maximum scale. """
        _, _, vw, vh = viewbox.getRect()
        width = self.w_board.width()
        height = self.w_board.height()
        scale = min(width / vw, height / vh)
        fw, fh = vw * scale, vh * scale
        ox = (width - fw) / 2
        oy = (height - fh) / 2
        return QRectF(ox, oy, fw, fh)

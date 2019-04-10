from cmath import phase, pi, rect
from typing import List

from PyQt5.QtCore import QPointF, QRectF
from PyQt5.QtGui import QColor, QPaintDevice, QPainter, QPainterPath, QPen, QTransform
from PyQt5.QtSvg import QSvgRenderer


class BoardSVGRenderer(QSvgRenderer):
    """ Renders SVG elements and other graphics on the steno board diagram. """

    def draw(self, target:QPaintDevice, element_info:List[tuple]) -> None:
        """ Draw the current steno key set, including transforms for scaling and offsetting. """
        last = []
        with BoardPainter(target) as p:
            for stroke, scale, ox, oy, in element_info:
                p.set_scale_offset(scale, ox, oy)
                for e_id in stroke:
                    if e_id == "INVERSION":
                        p.draw_inversion(last.pop(), last.pop())
                    else:
                        bounds = self.boundsOnElement(e_id)
                        last.append(bounds)
                        self.render(p, e_id, bounds)


class Point(complex):
    """ Represents a point in a path (either an endpoint or a Bezier control point). """

    @classmethod
    def from_qpoint(cls, p:QPointF):
        """ Convert a QPoint into a complex number. """
        return cls(p.x(), p.y())

    def control_point_between(self, ep:complex, shift_mag:float):
        """ The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
        midpoint = Point((self + ep) / 2)
        return midpoint.shift_toward(ep, shift_mag, pi / 2)

    def shift_toward(self, cp:complex, shift_mag:float, angle_offset:float=0.0):
        """ Back up an endpoint by <dist> units toward the control point to avoid covering up letters. """
        return Point(self + rect(shift_mag, phase(cp - self) + angle_offset))

    def __iter__(self):
        yield self.real
        yield self.imag


class BoardPainter(QPainter):
    """ Draws steno board graphics on a paint device. """

    # Graphics pen for inversion arrows.
    _ARROW_PEN = QPen(QColor(255, 0, 0))
    _ARROW_PEN.setWidthF(1.5)
    _ENDPOINT_SHIFT = 12.0
    _CURVE_SHIFT = 15.0

    def __init__(self, *args):
        """ Set anti-aliasing on for best quality. """
        super().__init__(*args)
        self.setRenderHints(QPainter.Antialiasing)

    def set_scale_offset(self, scale:float, ox:float, oy:float) -> None:
        """ Set the current transform based on the given scale and translation coefficients. """
        self.setTransform(QTransform(scale, 0, 0, scale, ox, oy))

    def draw_inversion(self, bounds1:QRectF, bounds2:QRectF) -> None:
        """ Draw 'recycle' pattern arrows connecting two elements that are inverted in steno order. """
        self.setPen(self._ARROW_PEN)
        # Get the general endpoints of the arrows from the bounds boxes of the affected elements.
        p1 = Point.from_qpoint(bounds1.center())
        p2 = Point.from_qpoint(bounds2.center())
        # Draw one arrow connecting the endpoints in each direction.
        self._draw_arrow(p1, p2)
        self._draw_arrow(p2, p1)

    def _draw_arrow(self, p_tail:Point, p_head:Point) -> None:
        """ Draw a bent arrow from <p_tail> to <p_head> using a quadratic Bezier curve. """
        # The control point is used to back up the endpoints, but must be recalculated afterwards.
        p_control = p_tail.control_point_between(p_head, self._CURVE_SHIFT)
        p_tail = p_tail.shift_toward(p_control, self._ENDPOINT_SHIFT)
        p_head = p_head.shift_toward(p_control, self._ENDPOINT_SHIFT)
        p_control = p_tail.control_point_between(p_head, self._CURVE_SHIFT)
        # Create a new arrow path with the required points and draw it.
        path = ArrowPath()
        path.draw_body(p_tail, p_control, p_head)
        path.draw_head(p_head, p_control)
        self.drawPath(path)


class ArrowPath(QPainterPath):

    _MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    _HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    _SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.

    def draw_body(self, p_tail:Point, p_control:Point, p_head:Point) -> None:
        self.moveTo(*p_tail)
        self.quadTo(*p_control, *p_head)

    def draw_head(self, p_head:Point, p_control:Point) -> None:
        h_len = self._MIN_HEAD_LENGTH + self.length() * self._HEAD_LENGTH_RATIO
        self.moveTo(*p_head.shift_toward(p_control, h_len, -self._SPREAD_ANGLE))
        self.lineTo(*p_head)
        self.lineTo(*p_head.shift_toward(p_control, h_len, self._SPREAD_ANGLE))

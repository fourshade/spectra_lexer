from cmath import phase, pi, rect
from typing import List

from .svg import SVGElement, SVGPath


class PathGenerator(List[str]):

    def _add_coords(self, cmd:str, *points:complex) -> None:
        coords = [f"{c:.2f}" for x in points for c in (x.real, x.imag)]
        self.extend([cmd, ",".join(coords)])

    def move_to(self, p:complex) -> None:
        """ Move to <p> and start a new primitive path. Must be called before using any drawing commands below. """
        self._add_coords("M", p)

    def line_to(self, ep:complex) -> None:
        """ Draw a simple line from the current position to <ep>. """
        self._add_coords("L", ep)

    def quad_to(self, cp:complex, ep:complex) -> None:
        """ Draw a quadratic Bezier curve from the current position to <ep> with control point <cp>. """
        self._add_coords("Q", cp, ep)

    def cubic_to(self, cp:complex, dp:complex, ep:complex) -> None:
        """ Draw a cubic Bezier curve from the current position to <ep> with control points <cp>, <dp>. """
        self._add_coords("C", cp, dp, ep)

    def close(self) -> None:
        """ After drawing with the above commands, close and fill a complete path. """
        self._add_coords("z")

    def finish(self) -> str:
        return "".join(self)


class PathInversion(PathGenerator):

    _SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.
    _HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    _MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    _CURVE_SHIFT = 15.0         # Amount to "bend" the arrow body outward perpendicular from the straight case.
    _ENDPOINT_SHIFT = 12.0      # Amount to pull the arrow endpoints back away from the element centers

    def draw(self, tail:complex, head:complex) -> None:
        """ Draw a bent arrow path from <tail> to <head>. The midpoint is used to back up the endpoints.
            The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
        control = self._get_control_point(head, tail)
        tail = self._shift_endpoint_to(tail, control)
        head = self._shift_endpoint_to(head, control)
        control = self._get_control_point(head, tail)
        body_length = abs(tail - head)
        h_len = self._MIN_HEAD_LENGTH + body_length * self._HEAD_LENGTH_RATIO
        spread = self._SPREAD_ANGLE
        head_pos = _shift_toward(head, control, h_len, -spread)
        head_neg = _shift_toward(head, control, h_len, spread)
        # Perform the actual drawing commands.
        self.move_to(head)
        self.quad_to(control, tail)
        self.quad_to(control, head)
        self.move_to(head)
        self.line_to(head_pos)
        self.move_to(head)
        self.line_to(head_neg)

    def _shift_endpoint_to(self, ep:complex, control:complex) -> complex:
        """ Back up an endpoint toward the control point to avoid covering up letters. """
        return _shift_toward(ep, control, self._ENDPOINT_SHIFT)

    def _get_control_point(self, head:complex, tail:complex) -> complex:
        midpoint = (tail + head) / 2
        return _shift_toward(midpoint, head, self._CURVE_SHIFT, pi / 2)


def _shift_toward(ep:complex, cp:complex, shift_mag:float, angle_offset:float=0.0) -> complex:
    return ep + rect(shift_mag, phase(cp - ep) + angle_offset)


class SVGPathInversion(SVGPath):
    """ Inversions are denoted by bent arrows drawn using a quadratic Bezier curve. """

    _STYLE = {"stroke": "#FF0000", "stroke-width": "1.5"}

    _ENDPOINT_SHIFT = 12.0      # Amount to pull the arrow endpoints back away from the element centers
    _CURVE_SHIFT = 15.0         # Amount to "bend" the arrow body outward perpendicular from the straight case.
    _MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    _HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    _SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.

    def __init__(self, *elems:SVGElement, **attrib):
        """ The SVG parser should have added offsets to eligible elements.
            Use these to determine the centers of the arrows. """
        path = PathInversion()
        p1, p2 = [getattr(elem, "offset", 0j) for elem in elems]
        path.draw(p1, p2)
        path.draw(p2, p1)
        # Add the stroke style for inversion arrows followed by the path string data.
        super().__init__(self._STYLE, d=path.finish(), **attrib)

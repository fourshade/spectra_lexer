from cmath import phase, pi, rect
from typing import List

from .svg import SVGElement, SVGPath, SVGGroup


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
        self.append("z")

    def finish(self) -> str:
        return "".join(self)


class PathInversion(PathGenerator):

    _ENDPOINT_SHIFT = 12.0      # Amount to pull the arrow endpoints back away from the element centers.
    _CURVE_SHIFT = 15.0         # Amount to "bend" the arrow body outward perpendicular from the straight case.
    _HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    _MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    _SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.

    def __init__(self, *args, width:float=0.0):
        super().__init__(*args)
        self._wshift = width / 2

    def draw(self, tail:complex, head:complex) -> str:
        """ Draw a bent arrow path from <tail> to <head>. Back up endpoints to avoid covering up letters.
            The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
        self.clear()
        i_control = self._get_control_point(tail, head)
        tail = self._shift_endpoint_to(tail, i_control)
        head = self._shift_endpoint_to(head, i_control)
        control = self._get_control_point(tail, head)
        self._draw_body(tail, head, control)
        self._draw_head(tail, head, control)
        return self.finish()

    def _draw_body(self, tail:complex, head:complex, control:complex) -> None:
        """ Shift the endpoints back a small amount to compensate for stroke width and draw the body. """
        ext_head = _shift_toward(head, control, -self._wshift)
        ext_tail = _shift_toward(tail, control, -self._wshift)
        self.move_to(ext_head)
        self.quad_to(control, ext_tail)
        self.quad_to(control, ext_head)

    def _draw_head(self, tail:complex, head:complex, control:complex) -> None:
        """ Draw the arrow head with length based on the overall body length and the stroke width adjustment. """
        body_length = abs(tail - head)
        h_len = self._MIN_HEAD_LENGTH + self._wshift + body_length * self._HEAD_LENGTH_RATIO
        spread = self._SPREAD_ANGLE
        for angle in (-spread, spread):
            self.move_to(head)
            self.line_to(_shift_toward(head, control, h_len, angle))

    def _shift_endpoint_to(self, ep:complex, control:complex) -> complex:
        """ Back up an endpoint toward the control point to avoid covering up letters. """
        return _shift_toward(ep, control, self._ENDPOINT_SHIFT)

    def _get_control_point(self, tail:complex, head:complex) -> complex:
        midpoint = (tail + head) / 2
        return _shift_toward(midpoint, head, self._CURVE_SHIFT, pi / 2)


def _shift_toward(ep:complex, cp:complex, shift_mag:float, angle_offset:float=0.0) -> complex:
    return ep + rect(shift_mag, phase(cp - ep) + angle_offset)


class SVGInversion(SVGGroup):
    """ Inversions are denoted by bent arrows drawn using a quadratic Bezier curve. """

    _STYLES = [{"stroke": "#800000", "stroke-width": "2.5"},
               {"stroke": "#FF0000", "stroke-width": "1.5"}]

    def __init__(self, *elems:SVGElement, **attrib):
        """ The SVG parser should have added offsets to eligible elements.
            Use these to determine the centers of the arrows. """
        super().__init__(**attrib)
        p1, p2 = [getattr(elem, "offset", 0j) for elem in elems]
        for style in self._STYLES:
            path_gen = PathInversion(width=float(style["stroke-width"]))
            for endpoints in ((p1, p2), (p2, p1)):
                self.append(SVGPath(style, d=path_gen.draw(*endpoints)))

from cmath import phase, pi, polar, rect
from math import ceil
from typing import List


def _fmt(x:complex) -> str:
    """ Format a complex number. Remove trailing zeros to reduce file size. """
    return f"{x.real:.4g},{x.imag:.4g}"


class PathGenerator(List[str]):
    """ Generates SVG path strings from a series of commands. """

    def move_to(self, p:complex, relative:bool=False) -> None:
        """ Move to <p> and start a new primitive path. Must be called before using any drawing commands below. """
        self += "m" if relative else "M", _fmt(p)

    def line_to(self, ep:complex, relative:bool=False) -> None:
        """ Draw a simple line from the current position to <ep>. """
        self += "l" if relative else "L", _fmt(ep)

    def quad_to(self, cp:complex, ep:complex, relative:bool=False) -> None:
        """ Draw a quadratic Bezier curve from the current position to <ep> with control point <cp>. """
        self += "q" if relative else "Q", _fmt(cp), _fmt(ep)

    def cubic_to(self, cp:complex, dp:complex, ep:complex, relative:bool=False) -> None:
        """ Draw a cubic Bezier curve from the current position to <ep> with control points <cp>, <dp>. """
        self += "c" if relative else "C", _fmt(cp), _fmt(dp), _fmt(ep)

    def arc_to(self, radii:complex, ep:complex, sweep_cw:bool=False, large_arc:bool=False, relative:bool=False) -> None:
        """ Draw an elliptical arc with x and y <radii> from the current position to <ep>.
            If <sweep_cw> is True, a clockwise arc is drawn, else it will be counter-clockwise.
            If <large_arc> is True, out of the two possible arc lengths, the one greater than 180 will be used. """
        self += "a" if relative else "A", _fmt(radii), f"0 {large_arc:d},{sweep_cw:d}", _fmt(ep)

    def close(self) -> None:
        """ After drawing with the above commands, close and fill a complete path. """
        self += "z",

    def draw(self, start:complex, end:complex, reverse:bool=False) -> None:
        """ Draw a path between two complex endpoints. """
        pass

    def to_string(self) -> str:
        return " ".join(self)


class PathInversion(PathGenerator):
    """ Inversions are denoted by bent arrows drawn using a quadratic Bezier curve. """

    ENDPOINT_SHIFT = 12.0      # Amount to pull the arrow endpoints back away from the element centers.
    CURVE_SHIFT = 15.0         # Amount to "bend" the arrow body outward perpendicular from the straight case.
    HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.

    def draw(self, tail:complex, head:complex, reverse:bool=False) -> None:
        """ Draw a bent arrow path from <tail> to <head>. Back up endpoints to avoid covering up letters.
            The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
        if reverse:
            tail, head = head, tail
        i_control = self._get_control_point(tail, head)
        tail = self._shift_endpoint_to(tail, i_control)
        head = self._shift_endpoint_to(head, i_control)
        control = self._get_control_point(tail, head)
        self._draw_body(tail, head, control)
        self._draw_head(tail, head, control)

    def _draw_body(self, tail:complex, head:complex, control:complex) -> None:
        self.move_to(head)
        self.quad_to(control, tail)

    def _draw_head(self, tail:complex, head:complex, control:complex) -> None:
        """ Draw the arrow head with length based on the overall body length. """
        body_length = abs(tail - head)
        h_len = self.MIN_HEAD_LENGTH + body_length * self.HEAD_LENGTH_RATIO
        spread = self.SPREAD_ANGLE
        for angle in (-spread, spread):
            self.move_to(head)
            self.line_to(self._shift_toward(head, control, h_len, angle))

    def _shift_endpoint_to(self, ep:complex, control:complex) -> complex:
        """ Back up an endpoint toward the control point to avoid covering up letters. """
        return self._shift_toward(ep, control, self.ENDPOINT_SHIFT)

    def _get_control_point(self, tail:complex, head:complex) -> complex:
        midpoint = (tail + head) / 2
        return self._shift_toward(midpoint, head, self.CURVE_SHIFT, pi / 2)

    @staticmethod
    def _shift_toward(ep:complex, cp:complex, shift_mag:float, angle_offset:float=0.0) -> complex:
        return ep + rect(shift_mag, phase(cp - ep) + angle_offset)


class PathChain(PathGenerator):
    """ For correct overlap, the entire chain must be divided into a top and bottom half.
        There are two major complications with this:
        1. For a given half of a single link, all of its layers must be composited before its successor is started.
           This requires multiple passes with different stroke widths and cannot be done using only path data.
        2. Any overlap on one half must be reversed for the other half to give the chain its linked appearance.
        An optimal solution is, for each data pass, draw *alternating* halves of the chain. After one pass, we have:
            //--------\\  //--------\\  //--------\\  //--------\\
            ||        ||  ||        ||  ||        ||  ||        ||
                   ||        ||  ||        ||  ||        ||  ||        ||
                   \\--------//  \\--------//  \\--------//  \\--------//
        None of these will interfere, so each layer can be immediately composited.
        The other set of alternating halves is drawn by switching the arc direction.
        All of the overlap happens in this second stage, and all links are intertwined in the correct manner. """

    LINK_RADIUS = 5.0  # Radius of the circular portions of a chain link.
    LINK_EXTEND = 5.0  # Length of the straight portion of a chain link.
    LINK_OFFSET = 3.0  # Approximate amount to shift each chain link inward toward its predecessor.

    _LINK_LENGTH = 2 * LINK_RADIUS + LINK_EXTEND  # Computed length of a single chain link.

    def draw(self, start:complex, end:complex, reverse:bool=False) -> None:
        """ Draw a chain path from <start> to <end> with alternating halves of each link. """
        length, angle = polar(end - start)
        offsets = [start + rect(off, angle) for off in self._link_offsets(length)]
        for half in (False, True):
            # Ensure that <reverse> always draws the missing side.
            direction = half ^ reverse
            self._draw_hemilinks(offsets[half::2], angle, direction)

    def _link_offsets(self, length:float) -> List[float]:
        """ Return a list of linear offsets for the beginning of each chain link.
            We adjust the spacing interval a little to provide equal spacing for an integer number of links. """
        body_length = self._LINK_LENGTH
        opt_spacing = body_length - self.LINK_OFFSET
        link_count = ceil(length / opt_spacing)
        if link_count == 1:
            return [0]
        actual_spacing = (length - body_length) / (link_count - 1)
        return [i * actual_spacing for i in range(link_count)]

    def _draw_hemilinks(self, offsets:List[complex], angle:float, direction_cw:bool=False):
        """ Draw one half of a chain link starting at every position in <offsets>.
            The first two moves can be relative, but the last one should be absolute for accurate shape closing. """
        radii = self.LINK_RADIUS * (1 + 1j)
        angle_out = (angle - pi / 4) if direction_cw else (angle + pi / 4)
        arc_move_out = rect(abs(radii), angle_out)
        line_move = rect(self.LINK_EXTEND, angle)
        arc_move_in = rect(self._LINK_LENGTH, angle)
        for start in offsets:
            self.move_to(start)
            self.arc_to(radii, arc_move_out, direction_cw, relative=True)
            self.line_to(line_move, relative=True)
            self.arc_to(radii, start + arc_move_in, direction_cw)

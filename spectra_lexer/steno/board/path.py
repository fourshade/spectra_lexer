from cmath import phase, pi, polar, rect
from math import ceil
from typing import List

from .svg import SVGPath


def _fmt(x:complex) -> str:
    """ Format a complex number as a coordinate pair. Remove trailing zeros to reduce file size. """
    return f"{x.real:.4g},{x.imag:.4g}"


class PathCommands(List[str]):
    """ List of SVG path command strings. """

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

    def to_string(self) -> str:
        """ Return an SVG path string from the current series of commands. """
        return " ".join(self)


class ConnectionPathCommands(PathCommands):
    """ Abstract class for commands that can connect two points. """

    def connect(self, start:complex, end:complex) -> None:
        """ Add commands for a path connecting two complex endpoints (with dummy implementation). """
        self.move_to(start)
        self.line_to(end)


class ArrowPathCommands(ConnectionPathCommands):
    """ Steno order inversions are denoted by curved arrows drawn using a quadratic Bezier curve. """

    ENDPOINT_SHIFT = 12.0      # Amount to pull the arrow endpoints back away from the element centers.
    CURVE_SHIFT = 15.0         # Amount to "bend" the arrow body outward perpendicular from the straight case.
    HEAD_LENGTH_RATIO = 0.033  # Extra length for head edges per unit of overall arrow length.
    MIN_HEAD_LENGTH = 5.0      # Minimum length for head edges (the lines that make the "point" of the arrow).
    SPREAD_ANGLE = pi / 8      # Angle in radians between each head edge and the arrow body.

    def connect(self, tail:complex, head:complex) -> None:
        """ Draw a curved arrow path from <tail> to <head>. Back up endpoints to avoid covering up letters.
            The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
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
        p_neg, p_pos = [self._shift_toward(head, control, h_len, angle) for angle in (-spread, spread)]
        self.move_to(p_neg)
        self.line_to(head)
        self.line_to(p_pos)

    def _shift_endpoint_to(self, ep:complex, control:complex) -> complex:
        """ Back up an endpoint toward the control point to avoid covering up letters. """
        return self._shift_toward(ep, control, self.ENDPOINT_SHIFT)

    def _get_control_point(self, tail:complex, head:complex) -> complex:
        midpoint = (tail + head) / 2
        return self._shift_toward(midpoint, head, self.CURVE_SHIFT, pi / 2)

    @staticmethod
    def _shift_toward(ep:complex, cp:complex, shift_mag:float, angle_offset:float=0.0) -> complex:
        return ep + rect(shift_mag, phase(cp - ep) + angle_offset)


class ChainPathCommands(ConnectionPathCommands):
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

    def connect(self, start:complex, end:complex) -> None:
        """ Draw one side of a chain path from <start> to <end> with alternating halves of each link.
            Calling this with the endpoints reversed will always draw the missing side. """
        reverse = (start.real < end.real)
        if reverse:
            start, end = end, start
        length, angle = polar(end - start)
        offsets = [start + rect(off, angle) for off in self._link_offsets(length)]
        for half in (False, True):
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

    def _draw_hemilinks(self, offsets:List[complex], angle:float, direction_cw:bool) -> None:
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


class LayeredPathList(List[SVGPath]):
    """ Contains layered SVG paths for bidirectional connections. """

    cmds_cls = ConnectionPathCommands  # Commands class to connect points with path data.
    layer_data = [(0j, "fill:none;")]  # Contains offsets and styles for layers in order from bottom to top.

    def connect(self, start:complex, end:complex) -> None:
        """ Add SVG path elements that compose paths between two endpoints in both directions.
            The paths are shifted by an optional offset after each iteration to create a drop shadow appearance. """
        for p1, p2 in ((start, end), (end, start)):
            path = ""
            for offset, style in self.layer_data:
                # If the path hasn't moved, don't regenerate the string data; it will be the same.
                if offset or not path:
                    cmds = self.cmds_cls()
                    cmds.connect(p1 + offset, p2 + offset)
                    path = cmds.to_string()
                self.append(SVGPath(d=path, style=style))


class ArrowPathList(LayeredPathList):

    cmds_cls = ArrowPathCommands
    layer_data = [(0j,  "fill:none;stroke:#800000;stroke-width:1.5px;"),
                  (-1j, "fill:none;stroke:#FF0000;stroke-width:1.5px;")]


class ChainPathList(LayeredPathList):

    cmds_cls = ChainPathCommands
    layer_data = [(0j, "fill:none;stroke:#000000;stroke-width:5.0px;"),
                  (0j, "fill:none;stroke:#B0B0B0;stroke-width:2.0px;")]

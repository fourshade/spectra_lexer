from cmath import phase, pi, rect
from math import ceil
from typing import List

from . import IPathCanvas


class ArrowPathGenerator:
    """ Draws curved arrows using quadratic Bezier curves. """

    endpoint_shift = 12.0      # Amount to "shrink" the arrow endpoints away from their given values.
    curve_shift = 15.0         # Amount to "bend" the center of the arrow body outward perpendicular.
    min_head_length = 5.0      # Starting length for head edges (the lines that make the "point" of the arrow).
    head_length_ratio = 0.033  # Additional length for head edges per unit of overall arrow length.
    spread_angle = pi / 8      # Angle in radians between each head edge and the arrow body.

    @staticmethod
    def _shift_toward(ep:complex, cp:complex, shift_mag:float, angle_offset=0.0) -> complex:
        return ep + rect(shift_mag, phase(cp - ep) + angle_offset)

    def _shift_endpoint_to(self, ep:complex, control:complex) -> complex:
        """ Back up an endpoint toward the control point. """
        return self._shift_toward(ep, control, self.endpoint_shift)

    def _get_control_point(self, tail:complex, head:complex) -> complex:
        midpoint = (tail + head) / 2
        return self._shift_toward(midpoint, head, self.curve_shift, pi / 2)

    def connect(self, tail:complex, head:complex, path:IPathCanvas) -> None:
        """ Add path commands for a curved arrow path from <tail> to <head>.
            Back up endpoints to avoid covering up letters.
            The control point starts on the line connecting the endpoints, then is shifted perpendicular to it. """
        i_control = self._get_control_point(tail, head)
        tail = self._shift_endpoint_to(tail, i_control)
        head = self._shift_endpoint_to(head, i_control)
        control = self._get_control_point(tail, head)
        # Draw the curved arrow body.
        path.move_to(head)
        path.quad_to(control, tail)
        # Draw the arrow head with length based on the overall body length.
        body_length = abs(tail - head)
        h_len = self.min_head_length + body_length * self.head_length_ratio
        spread = self.spread_angle
        p_neg, p_pos = [self._shift_toward(head, control, h_len, angle) for angle in (-spread, spread)]
        path.move_to(p_neg)
        path.line_to(head)
        path.line_to(p_pos)


class ChainPathGenerator:
    """ For correct overlap, the entire chain must be divided into a top and bottom half.
        There are two major complications with this:
        1. For a given half of a single link, all of its layers must be composited before its successor is started.
           This requires multiple passes with different stroke widths and cannot be done with a single path.
        2. Any overlap on one half must be reversed for the other half to give the chain its linked appearance.
        An optimal solution is to draw *alternating* halves of the chain as separate paths. One path looks like:
             //----------\\    //----------\\    //----------\\    //----------\\
            //            \\  //            \\  //            \\  //            \\
            ||       ||   ||  ||   ||  ||   ||  ||   ||  ||   ||  ||   ||  ||   ||       ||
                     \\            //  \\            //  \\            //  \\            //
                      \\----------//    \\----------//    \\----------//    \\----------//
        None of these overlap, so layer composition (to create shadow and outline effects) is safe.
        After these layers are finished, the other set of alternating halves may be rendered on top:
             //-------//----------\\----//----------\\----//----------\\----//----------\\
            //       //   \\  //   \\  //   \\  //   \\  //   \\  //   \\  //   \\       \\
            ||       ||   ||  ||   ||  ||   ||  ||   ||  ||   ||  ||   ||  ||   ||       ||
            \\       \\   //  \\   //  \\   //  \\   //  \\   //  \\   //  \\   //       //
             \\----------//----\\----------//----\\----------//----\\----------//-------//
        All of the overlap happens here, so all links are still intertwined correctly after layering. """

    link_length = 15.0  # Total length of a chain link.
    link_radius = 5.0   # Radius of the circular portions of a chain link.
    link_offset = 3.0   # Approximate amount to shift each chain link inward toward its predecessor.

    def _link_offsets(self, total_length:float) -> List[float]:
        """ Return a list of linear offsets for the origin of each chain link.
            We adjust the spacing interval a little to provide equal spacing for an integer number of links. """
        link_length = self.link_length
        exact_spacing = link_length - self.link_offset
        link_count = ceil(total_length / exact_spacing)
        if link_count == 1:
            return [0.0]
        actual_spacing = (total_length - link_length) / (link_count - 1)
        return [i * actual_spacing for i in range(link_count)]

    def _draw_hemilinks(self, path:IPathCanvas, origins:List[complex], unit_vec:complex, is_cw:bool) -> None:
        """ Draw a path for alternating halves of a chain link starting at every position in <origins>.
            If <is_cw> is True, start the first link with a clockwise arc and alternate from there. """
        radius = self.link_radius
        radii = radius * (1 + 1j)
        r_tan = radius * unit_vec
        arc_moves = [r_tan * (1 + 1j), r_tan * (1 - 1j)]
        end_offset = self.link_length * unit_vec
        line_move = end_offset - 2 * r_tan
        for start in origins:
            # The first and last movements for each link should be absolute for accurate shape closing.
            path.move_to(start)
            path.arc_to(radii, arc_moves[is_cw], is_cw, relative=True)
            path.line_to(line_move, relative=True)
            path.arc_to(radii, start + end_offset, is_cw)
            is_cw = not is_cw

    def connect(self, start:complex, end:complex, path:IPathCanvas, revpath:IPathCanvas=None) -> None:
        """ Add path commands for a complete chain path from <start> to <end>.
            If layers are required, pass two instances of PathCommands to draw each half separately. """
        vec = end - start
        length = abs(vec)
        unit_vec = vec / length
        origins = [start + unit_vec * offset for offset in self._link_offsets(length)]
        self._draw_hemilinks(path, origins, unit_vec, False)
        self._draw_hemilinks(revpath or path, origins, unit_vec, True)

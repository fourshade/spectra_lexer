""" Package for constructing SVG steno board diagrams. """

from typing import Sequence

Offset = Sequence[int]
OffsetSequence = Sequence[Offset]
Size = Sequence[int]


class IPathCanvas:
    """ Abstract path command canvas. """

    def move_to(self, p:complex, relative=False) -> None:
        """ Move to <p> and start a new primitive path. Must be called before using any drawing commands below. """
        raise NotImplementedError

    def line_to(self, ep:complex, relative=False) -> None:
        """ Draw a simple line from the current position to <ep>. """
        raise NotImplementedError

    def quad_to(self, cp:complex, ep:complex, relative=False) -> None:
        """ Draw a quadratic Bezier curve from the current position to <ep> with control point <cp>. """
        raise NotImplementedError

    def cubic_to(self, cp:complex, dp:complex, ep:complex, relative=False) -> None:
        """ Draw a cubic Bezier curve from the current position to <ep> with control points <cp>, <dp>. """
        raise NotImplementedError

    def arc_to(self, radii:complex, ep:complex, sweep_cw=False, large_arc=False, relative=False) -> None:
        """ Draw an elliptical arc with x and y <radii> from the current position to <ep>.
            If <sweep_cw> is True, a clockwise arc is drawn, else it will be counter-clockwise.
            If <large_arc> is True, out of the two possible arc lengths, the one greater than 180 will be used. """
        raise NotImplementedError

    def close(self) -> None:
        """ After drawing with the above commands, close and fill a complete path. """
        raise NotImplementedError


class IPathConnector:
    """ Abstract path canvas writer that connects points. """

    def connect(self, start:complex, end:complex, path:IPathCanvas) -> None:
        """ Draw a shape connecting <start> to <end> on a <path> canvas. """
        raise NotImplementedError


class ISerializable:
    """ Object that may be serialized into a string. """

    def __str__(self) -> str:
        raise NotImplementedError

from math import cos, pi, sin
from typing import Iterator, Sequence


class AffineTransform:
    """ 2D affine transformation.
        Any transform with scaling, rotation, translation, etc. can be composed into at most six coefficients.
        [ax, bx, cx]
        [ay, by, cy]
        [ 0,  0,  1] """

    __slots__ = ("_coefs",)

    def __init__(self) -> None:
        """ Start with the identity transform. """
        self._coefs = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)  # Transform coefficients [ax, ay, bx, by, cx, cy].

    def _mul(self, x1:float, y1:float, x2:float, y2:float, x3:float, y3:float) -> None:
        """ Apply a transform by matrix multiplication.
            [x1, x2, x3][ax, bx, cx]   [ax*x1+ay*x2, bx*x1+by*x2, cx*x1+cy*x2+x3]
            [y1, y2, y3][ay, by, cy] = [ax*y1+ay*y2, bx*y1+by*y2, cx*y1+cy*y2+y3]
            [ 0,  0,  1][ 0,  0,  1]   [          0,           0,              1] """
        ax, ay, bx, by, cx, cy = self._coefs
        self._coefs = (ax*x1+ay*x2, ax*y1+ay*y2, bx*x1+by*x2, bx*y1+by*y2, cx*x1+cy*x2+x3, cx*y1+cy*y2+y3)

    def rotate(self, degrees:float) -> None:
        """ Rotate the system <degrees> counterclockwise. """
        theta = degrees * pi / 180
        c = cos(theta)
        s = sin(theta)
        self._mul(c, -s, s, c, 0.0, 0.0)

    def scale(self, scale_x:float, scale_y:float) -> None:
        """ Grow or shrink the system by decimal scaling factors. """
        self._mul(scale_x, 0.0, 0.0, scale_y, 0.0, 0.0)

    def translate(self, x:float, y:float) -> None:
        """ Translate (move) the system by an additional offset of <x, y>. """
        self._mul(1.0, 0.0, 0.0, 1.0, x, y)

    def compose(self, other:'AffineTransform') -> None:
        """ Combine the effects of another transform with this one. """
        self._mul(*other._coefs)

    def coefs(self) -> Sequence[float]:
        """ Return all six transform coefficients in standard order. """
        return self._coefs


class TextOrientation:
    """ Possible orientation for fitting text inside a shape. """

    def __init__(self, width:float, angle:float=0.0, weight:float=1.0) -> None:
        self.width = width    # Available width in pixels at this orientation.
        self.angle = angle    # Rotation angle in degrees, CCW positive.
        self.weight = weight  # Preference factor for this orientation.


TextOrientations = Sequence[TextOrientation]
TransformIter = Iterator[AffineTransform]


class TextTransformer:
    """ Generates transforms to fit monospaced text glyphs inside irregular shapes.
        Glyphs are defined using standard typography conventions and units. """

    def __init__(self, font_size_px:float, em_size:int, tracking:int, baseline:int) -> None:
        self._font_size_px = font_size_px  # Size of each character in pixels if no adjustment is needed.
        self._em_size = em_size            # Size of each character in the native transform units.
        self._tracking = tracking          # Spacing between characters in native units.
        self._baseline = baseline          # Baseline height above the origin in native units.

    def _iter_base_tfrms(self, n:int) -> TransformIter:
        """ Yield an unscaled transform for each character of an origin-centered string of length <n>. """
        y = self._baseline - (self._em_size / 2)
        for i in range(n):
            x = (i - n / 2) * self._tracking
            tfrm = AffineTransform()
            tfrm.translate(x, y)
            yield tfrm

    def _best_lin_tfrm(self, n:int, orients:TextOrientations) -> AffineTransform:
        """ Choose the best-fitting scale and rotation for <n> characters from a sequence of orientations.
            The y-axis must be inverted since typography defines +y=up, but computer graphics is +y=down. """
        max_width_native = n * self._tracking
        max_width_px = max_width_native * self._font_size_px / self._em_size
        if not orients:
            best = TextOrientation(max_width_px)
        else:
            best = max(orients, key=lambda o: min(o.width, max_width_px) * o.weight)
        width_px = min(best.width, max_width_px)
        scale = width_px / max_width_native
        tfrm = AffineTransform()
        tfrm.scale(scale, -scale)
        tfrm.rotate(best.angle)
        return tfrm

    def iter_transforms(self, n:int, orients:TextOrientations) -> TransformIter:
        """ Yield an affine transform for each character in a string of length <n> centered at the origin. """
        if n <= 0:
            return
        lin_tfrm = self._best_lin_tfrm(n, orients)
        for tfrm in self._iter_base_tfrms(n):
            tfrm.compose(lin_tfrm)
            yield tfrm

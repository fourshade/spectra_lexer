from typing import Dict, List, NoReturn

IntDict = Dict[str, int]
StrDict = Dict[str, str]
ProcsDict = Dict[str, StrDict]


class Struct:
    """ Basic immutable attribute-based data structure. """

    def __init__(self, **attrs) -> None:
        self.__dict__.update(attrs)

    def __setattr__(self, *args) -> NoReturn:
        raise AttributeError('Structure is immutable.')


class FillColors(Struct):
    """ Namespace for background colors as HTML/SVG hex strings. """

    base: str
    matched: str
    unmatched: str
    letters: str
    alt: str
    rare: str
    combo: str
    number: str
    symbol: str
    spelling: str
    brief: str


class StenoBoardDefinitions:
    """ Contains various graphical definitions required to draw steno board diagrams. """

    def __init__(self, *, bounds:IntDict, offsets:Dict[str, List[int]], colors:StrDict, shapes:Dict[str, dict],
                 font:IntDict, glyphs:StrDict, keys:ProcsDict, rules:ProcsDict, **unused) -> None:
        self.bounds = bounds    # Coordinates of the bounding box for a single board diagram (before transforms).
        self.offsets = offsets  # Dict of [x, y] offset coordinates for the upper-left corner of every key on the board.
        self.colors = colors    # Dict of background colors for steno key shapes.
        self.shapes = shapes    # Dict of instructions for creating each key shape in SVG.
        self.font = font        # Dict of font sizing properties for raw glyphs.
        self.glyphs = glyphs    # Dict of single Unicode characters mapped to SVG path data strings with their outlines.
        self.keys = keys        # Dict of single steno s-keys mapped to full definitions of their appearance.
        self.rules = rules      # Dict of s-keys sequences mapped to compound key shapes with space for rule text.

    _field_types = __init__.__annotations__

    def verify(self) -> None:
        """ Perform type checks on instance fields using the signature of __init__. """
        for k, v in vars(self).items():
            if k in self._field_types:
                # isinstance() breaks if a type check is made for Dict[whatever].
                # just check for "dict" until the typing module gets its shit together.
                sig_tp = dict
                if not isinstance(v, sig_tp):
                    raise TypeError(f'Field "{k}" must be {sig_tp.__name__}, got {type(v).__name__}.')

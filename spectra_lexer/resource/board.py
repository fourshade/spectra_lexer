from typing import Dict, List, Mapping

from . import FrozenStruct

IntDict = Dict[str, int]
StrDict = Dict[str, str]
OffsetDict = Dict[str, List[int]]
ShapeDict = Dict[str, dict]
ProcsDict = Dict[str, StrDict]


class FillColors(FrozenStruct):
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


class StenoBoardDefinitions(FrozenStruct):
    """ Contains various graphical definitions required to draw steno board diagrams. """

    bounds:  IntDict     # Coordinates of the bounding box for a single board diagram (before transforms).
    offsets: OffsetDict  # Dict of [x, y] coordinates for the upper-left corner of every key on the board.
    colors:  StrDict     # Dict of background colors for steno key shapes.
    shapes:  ShapeDict   # Dict of instructions for creating each key shape in SVG.
    font:    IntDict     # Dict of font sizing properties for raw glyphs.
    glyphs:  StrDict     # Dict of single Unicode characters mapped to SVG path data strings with their outlines.
    keys:    ProcsDict   # Dict of single steno s-keys mapped to full definitions of their appearance.
    rules:   ProcsDict   # Dict of s-keys sequences mapped to compound key shapes with space for rule text.

    def verify(self) -> None:
        """ Perform type checks on instance fields using annotations. """
        for k, v in vars(self).items():
            if k in self.__annotations__:
                # isinstance() breaks if a type check is made for Mapping[whatever].
                # they are all mappings; just check the base type until the typing module gets its shit together.
                sig_tp = Mapping
                if not isinstance(v, sig_tp):
                    raise TypeError(f'Field "{k}" must be {sig_tp.__name__}, got {type(v).__name__}.')

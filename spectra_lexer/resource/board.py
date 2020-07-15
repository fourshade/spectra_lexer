from typing import Dict, get_origin, List

IntDict = Dict[str, int]
StrDict = Dict[str, str]
ProcsDict = Dict[str, StrDict]


class StenoBoardDefinitions:
    """ Contains various graphical definitions required to draw steno board diagrams. """

    def __init__(self, *, bounds:IntDict, offsets:Dict[str, List[int]], shapes:Dict[str, dict],
                 font:IntDict, glyphs:StrDict, keys:ProcsDict, rules:ProcsDict, **unused) -> None:
        self.bounds = bounds    # Coordinates of the bounding box for a single board diagram (before transforms).
        self.offsets = offsets  # Dict of [x, y] offset coordinates for the upper-left corner of every key on the board.
        self.shapes = shapes    # Dict of instructions for creating each key shape in SVG.
        self.font = font        # Dict of font sizing properties for raw glyphs.
        self.glyphs = glyphs    # Dict of single Unicode characters mapped to SVG path data strings with their outlines.
        self.keys = keys        # Dict of single steno s-keys mapped to full definitions of their appearance.
        self.rules = rules      # Dict of s-keys sequences mapped to compound key shapes with space for rule text.

    _param_types = __init__.__annotations__

    def _type_check(self, k:str) -> None:
        """ Check if field <k> matches the type in the signature of __init__. """
        tp = self._param_types[k]
        origin = get_origin(tp)
        if origin is not None:
            tp = origin
        v_tp = type(getattr(self, k))
        if not issubclass(v_tp, tp):
            raise TypeError(f'Field "{k}" must be {tp.__name__}, got {v_tp.__name__}.')

    def verify(self) -> None:
        """ Perform basic type checks on instance fields. """
        for k in vars(self):
            if k in self._param_types:
                self._type_check(k)

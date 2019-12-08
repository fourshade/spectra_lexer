from typing import Dict, List, Tuple


class StenoBoardDefinitions:
    """ Contains various graphical definitions required to draw steno board diagrams. """

    def __init__(self, defs:Dict[str, dict]) -> None:
        self._defs = defs

    @property
    def offsets(self) -> Dict[str, List[int]]:
        """ Return a dict of [x, y] offset coordinates for the upper-left corner of every key on the board. """
        return self._defs["pos"]

    @property
    def shapes(self) -> Dict[str, dict]:
        """ Return a dict of key shape attribute dicts. """
        return self._defs["shape"]

    @property
    def glyphs(self) -> Dict[str, str]:
        """ Return a dict of single Unicode characters mapped to SVG path data strings with their outlines. """
        return self._defs["glyph"]

    @property
    def keys(self) -> Dict[str, List[str]]:
        """ Return a dict of single steno s-keys mapped to full definitions of their appearance. """
        return self._defs["key"]

    @property
    def rules(self) -> Dict[str, List[str]]:
        """ Return a dict of s-keys sequences mapped to compound key shapes with space for rule text. """
        return self._defs["rule"]

    @property
    def bounds(self) -> Tuple[int, int, int, int]:
        """ Return the coordinates of the bounding box for a single board diagram (before transforms). """
        bounds = self._defs["bounds"]
        x, y = bounds["min"]
        w, h = bounds["max"]
        return x, y, w, h

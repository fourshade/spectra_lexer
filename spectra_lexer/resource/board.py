from typing import Dict, List


class StenoBoardDefinitions:
    """ Contains various graphical definitions required to draw steno board diagrams. """

    def __init__(self, *, bounds:Dict[str, int], offsets:Dict[str, List[int]], shapes:Dict[str, dict],
                 glyphs:Dict[str, str], keys:Dict[str, List[str]], rules:Dict[str, List[str]], **unused) -> None:
        self.bounds = bounds    # Coordinates of the bounding box for a single board diagram (before transforms).
        self.offsets = offsets  # Dict of [x, y] offset coordinates for the upper-left corner of every key on the board.
        self.shapes = shapes    # Dict of instructions for creating each key shape in SVG.
        self.glyphs = glyphs    # Dict of single Unicode characters mapped to SVG path data strings with their outlines.
        self.keys = keys        # Dict of single steno s-keys mapped to full definitions of their appearance.
        self.rules = rules      # Dict of s-keys sequences mapped to compound key shapes with space for rule text.

    @classmethod
    def from_json_dict(cls, d:dict) -> "StenoBoardDefinitions":
        """ Create a definitions structure from a JSON dict unpacked as **kwargs. """
        try:
            return cls(**d)
        except TypeError as e:
            raise TypeError("Board graphics definitions are incomplete") from e

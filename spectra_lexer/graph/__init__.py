""" Package for constructing text graphs of steno rules. """

from typing import Container, Iterator


class IBody:

    __slots__ = ()

    def height(self) -> int:
        """ Return the height of the node body in rows. """
        raise NotImplementedError

    def width(self) -> int:
        """ Return the width of the node body in columns. """
        raise NotImplementedError

    def is_always_bold(self) -> bool:
        raise NotImplementedError

    def is_separator(self) -> bool:
        raise NotImplementedError

    def text(self) -> str:
        """ Return a string of text to write as a row. """
        raise NotImplementedError

    def offset(self) -> int:
        """ Return a column offset for where text should be written. """
        raise NotImplementedError


ConnectorRows = Iterator[str]


class IConnectors:
    """ A set of connector characters joining a node to its parent. """

    __slots__ = ()

    def rows(self, height:int) -> ConnectorRows:
        """ Yield <height> row strings going downward, starting with the row under the parent. """
        raise NotImplementedError

    def min_height(self) -> int:
        """ Minimum height is 3 characters, or 2 if the bottom attachment is one character wide. """
        raise NotImplementedError


class TextElement:
    """ A single text element with markup. Corresponds to exactly one printed character. """

    __slots__ = ["char", "ref", "color_index", "bold_at", "activators"]

    def __init__(self, char:str, ref="", color_index=0, bold_at=10, activators:Container[str]=()) -> None:
        self.char = char                # Printed text character.
        self.ref = ref                  # Primary ref string - links to the node that was responsible for this element.
        self.color_index = color_index  # Numerical index to a table of RGB colors.
        self.bold_at = bold_at          # 0 = always bold, 1 = bold when activated, >1 = never bold.
        self.activators = activators    # Contains all refs that will activate (highlight) this element.

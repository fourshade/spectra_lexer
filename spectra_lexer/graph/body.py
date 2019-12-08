""" Module for styling the appearance of keys and translations in text graphs. """

from typing import Tuple

from .base import IBody


class SeparatorBody(IBody):
    """ The singular stroke separator node. It is not connected to anything and may be removed by the layout. """

    def __init__(self, key:str) -> None:
        assert len(key) == 1
        self._key = key  # The singular stroke separator character.

    def height(self) -> int:
        """ A separation line will try to 'occupy' one row of space and force other nodes down to the next row. """
        return 1

    def width(self) -> int:
        """ Separators go under everything else; they do not occupy any column space on the layout. """
        return 0

    def is_always_bold(self) -> bool:
        return False

    def is_separator(self) -> bool:
        return True

    def text(self, col:int) -> Tuple[int, str]:
        return col, self._key


class StandardBody(IBody):
    """ A standard node in a tree structure of steno rules. """

    def __init__(self, text:str) -> None:
        self._text = text  # Text characters drawn on the last row as the node's "body".

    def height(self) -> int:
        """ All current node bodies are exactly one row of text. """
        return 1

    def width(self) -> int:
        return len(self._text)

    def is_always_bold(self) -> bool:
        return False

    def is_separator(self) -> bool:
        return False

    def text(self, col:int) -> Tuple[int, str]:
        return col, self._text


class ShiftedBody(StandardBody):
    """ This node text may have an additional shift offset. """

    def __init__(self, text:str, col_offset:int) -> None:
        super().__init__(text)
        self._col_offset = col_offset

    def width(self) -> int:
        """ The body width must account for the column shift. """
        return len(self._text) + self._col_offset

    def text(self, col:int) -> Tuple[int, str]:
        """ Return the text after shifting to account for hyphens. """
        return col + self._col_offset, self._text


class BoldBody(StandardBody):

    def is_always_bold(self) -> bool:
        return True

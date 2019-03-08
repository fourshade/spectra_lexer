from typing import Iterable, List

from spectra_lexer.steno.keys import StenoKeys

# Pre-made element IDs.
_BACKGROUND_IDS = ["Base"]
_SEP_ID = StenoKeys.separator()


class DiagramElements(List[List[str]]):
    """ List of diagrams, each containing a list of element ID strings that make up a single stroke. """

    def __init__(self, elements:Iterable[str]):
        """ Split an iterable of elements at each stroke separator and add the background to each stroke. """
        super().__init__()
        elements = list(elements)
        start = 0
        for i, element in enumerate(elements):
            if _SEP_ID in element:
                self.append(_BACKGROUND_IDS + elements[start:i])
                start = i + 1
        self.append(_BACKGROUND_IDS + elements[start:])

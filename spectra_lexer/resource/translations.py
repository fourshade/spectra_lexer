""" Defines data types for JSON-compatible steno translations. """

from typing import Dict, Iterable, Tuple

Translation = Tuple[str, str]                  # A steno translation as a pair of strings: (RTFCRE keys, letters).
TranslationsIter = Iterable[Translation]       # Iterable collection of steno translations.
TranslationsDict = Dict[str, str]              # Dictionary mapping RTFCRE keys to letters.
RuleID = str                                   # Rule ID data type. Must be a string to act as a JSON object key.
ExamplesDict = Dict[RuleID, TranslationsDict]  # Dictionary mapping rule identifiers to example translation dicts.


class TranslationFilter:
    """ Filter for RTFCRE steno translations based on string size. """

    SIZE_MINIMUM = 0   # At this size and below, the filter blocks everything.
    SIZE_DEFAULT = 12  # Reasonable default size for casual analysis.
    SIZE_MAXIMUM = 20  # At this size and above, the filter is disabled.

    def __init__(self, size:int=None) -> None:
        if size is None:
            size = self.SIZE_DEFAULT
        self._size = size

    def filter(self, translations:TranslationsIter) -> TranslationsIter:
        """ Return a list of translations where neither string is longer than the filter size. """
        size = self._size
        if size <= self.SIZE_MINIMUM:
            # If the size is minimum, it is probably a dummy run. Keep nothing.
            filtered = []
        elif size >= self.SIZE_MAXIMUM:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            filtered = [*translations]
        else:
            # Eliminate long translations depending on the size factor.
            filtered = [(keys, letters) for keys, letters in translations
                        if len(keys) <= size and len(letters) <= size]
        return filtered

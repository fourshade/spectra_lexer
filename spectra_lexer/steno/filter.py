from typing import Dict


class TranslationSizeFilter:
    """ Filter for translations based on their size.  """

    MINIMUM_SIZE = 1   # Below this size, the filter blocks everything.
    SMALL_SIZE = 10
    MEDIUM_SIZE = 12
    LARGE_SIZE = 15
    MAXIMUM_SIZE = 20  # At this size and above, the filter is disabled.

    def __init__(self, size:int=None) -> None:
        self._size = size or self.MEDIUM_SIZE  # Maximum allowed length of any string in a translation.

    def filter(self, translations:Dict[str, str]) -> Dict[str, str]:
        """ Return a new dict with <translations> filtered according to the required maximum size. """
        size = self._size
        if size < self.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            return {}
        elif size >= self.MAXIMUM_SIZE:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            return dict(translations)
        # Eliminate long translations depending on the size factor.
        return {keys: letters for keys, letters in translations.items()
                if len(keys) <= size and len(letters) <= size}

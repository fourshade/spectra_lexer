from typing import Dict, Iterable


class ExampleIndexInfo:
    """ Contains constants regarding index generation. """

    def __init__(self) -> None:
        # Relative index size (1-20). Essentially the maximum word length.
        self._minimum_size = 1   # Below this size, input filters block everything.
        self._small_size = 10
        self._medium_size = 12
        self._large_size = 15
        self._maximum_size = 20  # At this size and above, input filters are disabled.

    def default_size(self) -> int:
        return self._medium_size

    def minimum_size(self) -> int:
        return self._minimum_size

    def maximum_size(self) -> int:
        return self._maximum_size

    def size_descriptions(self) -> Iterable[str]:
        return [f"size = {self._minimum_size}: includes nothing.",
                f"size = {self._small_size}: fast index with relatively simple words.",
                f"size = {self._medium_size}: average-sized index (default).",
                f"size = {self._large_size}: slower index with more advanced words.",
                f"size = {self._maximum_size}: includes everything."]

    def filter_translations(self, translations:Dict[str, str], size:int=None) -> Dict[str, str]:
        """ Return a new dict with input translations filtered according to the required index size. """
        if size is None:
            size = self.default_size()
        elif size < self._minimum_size:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            return {}
        elif size >= self._maximum_size:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            return translations.copy()
        # Eliminate long translations before processing depending on the size factor.
        return {keys: letters for keys, letters in translations.items()
                if len(keys) <= size and len(letters) <= size}

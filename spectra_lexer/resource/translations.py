""" Module for working with raw RTFCRE translations from disk. """

import json
from typing import Dict


class RTFCREDict(Dict[str, str]):
    """ Dict of RTFCRE steno translations. """

    # Cutoffs for translation filters based on their size.
    FSIZE_MINIMUM = 1   # Below this size, the filter blocks everything.
    FSIZE_SMALL = 10
    FSIZE_MEDIUM = 12
    FSIZE_LARGE = 15
    FSIZE_MAXIMUM = 20  # At this size and above, the filter is disabled.
    # Ordered list of all filter sizes for GUI display.
    FILTER_SIZES = [FSIZE_MINIMUM, FSIZE_SMALL, FSIZE_MEDIUM, FSIZE_LARGE, FSIZE_MAXIMUM]

    def size_filtered(self, size:int=None) -> "RTFCREDict":
        """ Return a new dict including only translations below a maximum size.
            <size> is the maximum allowed length of any string in a translation. """
        cls = type(self)
        if size is None:
            size = self.FSIZE_MEDIUM
        if size < self.FSIZE_MINIMUM:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            filtered = cls()
        elif size >= self.FSIZE_MAXIMUM:
            # If the size is maximum, filtering is unnecessary. Keep everything.
            filtered = cls(self)
        else:
            # Eliminate long translations depending on the size factor.
            filtered = cls()
            for keys, letters in self.items():
                if len(keys) <= size and len(letters) <= size:
                    filtered[keys] = letters
        return filtered

    @classmethod
    def from_json_files(cls, *filenames:str) -> "RTFCREDict":
        """ Load and merge translations from JSON files. UTF-8 is explicitly required for some translations. """
        self = cls()
        for filename in filenames:
            with open(filename, 'r', encoding='utf-8') as fp:
                d = json.load(fp)
            if not isinstance(d, dict):
                raise TypeError(f'Steno translations file "{filename}" does not contain a string dict.')
            self.update(d)
        return self


class RTFCREExamplesDict(Dict[str, RTFCREDict]):
    """ Dict of RTFCRE example translation dicts keyed by rule ID. """

    @classmethod
    def from_json_file(cls, filename:str) -> "RTFCREExamplesDict":
        """ Load example translations from a JSON file. UTF-8 is explicitly required for some translations. """
        with open(filename, 'r', encoding='utf-8') as fp:
            d = json.load(fp)
        if not isinstance(d, dict) or not all([isinstance(v, dict) for v in d.values()]):
            raise TypeError(f'Examples index file "{filename}" does not contain a dict of dicts.')
        return cls(d)

    def json_dump(self, filename:str) -> None:
        """ Save this dict to a JSON file. Key sorting helps some algorithms run faster.
            An explicit flag is required to preserve Unicode symbols. """
        with open(filename, 'w', encoding='utf-8') as fp:
            json.dump(self, fp, sort_keys=True, ensure_ascii=False)

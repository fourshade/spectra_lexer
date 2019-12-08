""" Module for working with raw RTFCRE translations from disk. """

from configparser import ConfigParser
import json
import os
from typing import Dict


class RTFCREDict(Dict[str, str]):
    """ Dict of RTFCRE steno translations. """

    class FilterSizes:
        """ Cutoffs for translation filters based on their size. """
        MINIMUM_SIZE = 1   # Below this size, the filter blocks everything.
        SMALL_SIZE = 10
        MEDIUM_SIZE = 12
        LARGE_SIZE = 15
        MAXIMUM_SIZE = 20  # At this size and above, the filter is disabled.

    def size_filtered(self, size:int=None) -> "RTFCREDict":
        """ Return a new dict including only translations below a maximum size.
            <size> is the maximum allowed length of any string in a translation. """
        cls = type(self)
        if size is None:
            size = self.FilterSizes.MEDIUM_SIZE
        if size < self.FilterSizes.MINIMUM_SIZE:
            # If the size is below minimum, it could be a dummy run. Keep nothing.
            filtered = cls()
        elif size >= self.FilterSizes.MAXIMUM_SIZE:
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

    @classmethod
    def from_plover_cfg(cls, cfg_filename:str, *, ignore_errors=True,
                        system_key='System: English Stenotype', option_key='dictionaries') -> "RTFCREDict":
        """ Parse the dictionaries section of a Plover CFG and add the contents of all dictionaries in order. """
        try:
            parser = ConfigParser()
            with open(cfg_filename, 'r', encoding='utf-8') as fp:
                parser.read_file(fp)
            # Dictionaries are located in the same directory as the config file.
            # The config value we need is read as a string, but it must be decoded as a JSON array of objects.
            value = parser[system_key][option_key]
            dictionary_specs = json.loads(value)
            plover_dir = os.path.split(cfg_filename)[0]
            # Earlier keys override later ones in Plover, but dict.update does the opposite. Reverse the priority order.
            files = [os.path.join(plover_dir, spec['path']) for spec in reversed(dictionary_specs)]
            return cls.from_json_files(*files)
        except (IndexError, KeyError, OSError, ValueError):
            # Catch-all for file and parsing errors. Return an empty dict if <ignore_errors> is True.
            if not ignore_errors:
                raise
            return cls()


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

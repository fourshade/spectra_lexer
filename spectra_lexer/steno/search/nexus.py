""" Module with instances and groupings of specialized string search dictionaries by the resource they represent. """

from typing import Dict, Optional

from .special import ReverseStenoSearchDict, StenoSearchDict


class ResourceNexus:

    PRIORITY = 0  # Search priority. Resource prefixes are checked in order from highest to lowest priority nexus.

    def check(self, pattern:str, **mode_kwargs) -> Optional[tuple]:
        """ Default dict return function that never works. """


class TranslationNexus(ResourceNexus):
    """ A hybrid forward+reverse steno translation search dict. """

    _forward: StenoSearchDict
    _reverse: ReverseStenoSearchDict

    def __init__(self, d:Dict[str, str]):
        """ For translation-based searches, spaces and hyphens should be stripped off each end. """
        self._forward = StenoSearchDict(d, " -")
        self._reverse = ReverseStenoSearchDict(d, " -")

    def check(self, pattern:str, strokes:bool=False, **mode_kwargs) -> Optional[tuple]:
        """ Dict return function that works if nothing else matches. """
        return (self._forward if strokes else self._reverse), pattern


class RulesNexus(StenoSearchDict, ResourceNexus):

    PRIORITY = 1

    def __init__(self, d:dict):
        """ To search the rules dictionary by name, prefix and suffix reference symbols should be stripped. """
        super().__init__(d, " .+-~")

    def check(self, pattern:str, **mode_kwargs) -> Optional[tuple]:
        """ Dict return function for a rules search. """
        if pattern.startswith("/"):
            return self, pattern[1:]

    def command(self, match:str, mapping:object) -> tuple:
        """ If the mapping is a rule, send it as direct output just like the lexer would and return. """
        return "new_lexer_result", mapping


class IndexNexus(ResourceNexus):

    PRIORITY = 2

    _dicts: Dict[str, TranslationNexus]

    def __init__(self, d:Dict[str, dict]):
        """ Index search goes by rule name, and is very precise. Only exact matches will work. """
        self._dicts = {k: TranslationNexus(v) for k, v in d.items()}

    def check(self, pattern:str, **mode_kwargs) -> Optional[tuple]:
        """ Dict return function for an index search. Strip the prefix to get the dict:pattern combo. """
        if pattern.startswith("//"):
            key, *pattern = pattern[2:].split(":", 1)
            if key in self._dicts:
                return self._dicts[key], (pattern or "")

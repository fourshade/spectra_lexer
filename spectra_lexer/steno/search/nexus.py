""" Module with instances and groupings of specialized string search dictionaries by the resource they represent. """

from typing import Dict, Optional

from spectra_lexer.steno.search.strip_case import ReverseStripCaseSearchDict, StripCaseSearchDict
from spectra_lexer.utils import delegate_to


class ResourceNexus:

    PRIORITY: int = 0  # Search priority. Resource prefixes are checked in order from highest to lowest priority nexus.

    _d: StripCaseSearchDict = StripCaseSearchDict()  # Current dict used for lookups and commands.

    def check(self, pattern:str, **mode_kwargs) -> Optional[str]:
        """ Indicator function that returns a new pattern on success and can modify the current dict reference. """
        raise NotImplementedError

    def command(self, match:str, mapping:object) -> tuple:
        """ Return a tuple of items that can be directly called as an engine command to show a result. """
        raise NotImplementedError

    search = delegate_to("_d")
    get_list = delegate_to("_d")


class TranslationNexus(ResourceNexus):
    """ A hybrid forward+reverse steno translation nexus. Used when nothing else matches. """

    CMD_KEY: str = "show_translation"  # Key for engine command.

    _forward: StripCaseSearchDict         # Forward translations dict (strokes -> English words).
    _reverse: ReverseStripCaseSearchDict  # Reverse translations dict (English words -> strokes).

    def __init__(self, d:Dict[str, str]):
        """ For translation-based searches, spaces and hyphens should be stripped off each end. """
        self._forward = StripCaseSearchDict(d, " -")
        self._reverse = ReverseStripCaseSearchDict(d, " -")

    def check(self, pattern:str, strokes:bool=False, **mode_kwargs) -> Optional[str]:
        """ Indicator function that always returns success. Does not modify the pattern. """
        self._d = self._forward if strokes else self._reverse
        return pattern

    def command(self, match:str, mapping:object) -> tuple:
        """ The order of strokes/word in the lexer command is reversed for a reverse dict. """
        args = (match, mapping) if self._d is self._forward else (mapping, match)
        return (self.CMD_KEY, *args)


class RulesNexus(ResourceNexus):
    """ A simple nexus for rule search by name when a prefix is added. There is only one dict which never changes. """

    PRIORITY = 1                 # Has medium priority. It must outrank the translations nexus only.
    PREFIX: str = "/"            # A basic slash which is also a prefix of *other*, higher priority prefixes.
    CMD_KEY: str = "new_output"  # Key for engine command.

    def __init__(self, d:dict):
        """ To search the rules dictionary by name, prefix and suffix reference symbols should be stripped. """
        self._d = StripCaseSearchDict(d, " .+-~")

    def check(self, pattern:str, **mode_kwargs) -> Optional[str]:
        """ Indicator function for a rules search. Requires a simple prefix which is removed. """
        if pattern.startswith(self.PREFIX):
            return pattern[1:]

    def command(self, match:str, mapping:object) -> tuple:
        """ If the mapping is a rule, send it as direct output just like the lexer would and return. """
        return self.CMD_KEY, mapping


class IndexNexus(ResourceNexus):
    """ A resource-heavy nexus for finding translations that contain a particular steno rule. """

    PRIORITY = 2        # Has highest priority but lowest chance of success. Must outrank the rules nexus.
    PREFIX: str = "//"  # This includes the rules prefix, so it must be checked first.

    _children: Dict[str, TranslationNexus]  # Dict containing a whole subnexus for every rule name.
    _d: TranslationNexus                    # Current nexus used to redirect checks and commands.

    def __init__(self, d:Dict[str, dict]):
        """ Index search is a two-part search. The first part goes by rule name, and is very precise.
            It is a key to a dict of child nexus objects, so only exact matches will work. """
        self._children = {k: TranslationNexus(v) for k, v in d.items()}
        self._d = TranslationNexus({})

    def check(self, pattern:str, **mode_kwargs) -> Optional[str]:
        """ Indicator function for a rules search. Strip the prefix to get the subnexus:pattern combo. """
        if pattern.startswith(self.PREFIX):
            key, pattern = (pattern[2:].split(":", 1) + [""])[:2]
            if key in self._children:
                self._d = self._children[key]
                return self._d.check(pattern, **mode_kwargs)

    command = delegate_to("_d")

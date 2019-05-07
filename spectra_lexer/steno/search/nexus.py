""" Module with instances and groupings of specialized string search dictionaries by the resource they represent. """

from typing import Dict, Optional

from .dict import ReverseStripCaseSearchDict, StripCaseSearchDict
from spectra_lexer.types import delegate_to, polymorph_index
from spectra_lexer.utils import ensure_iterable


class ResourceNexus:

    PRIORITY: int = 0  # Search priority. Resource prefixes are checked in order from highest to lowest priority nexus.
    PREFIX: str = ""   # Prefix to test (and strip) on input patterns. Empty by default, so pattern is unmodified.

    _d: StripCaseSearchDict = StripCaseSearchDict()  # Current dict used for lookups and commands.

    types = polymorph_index()  # Records nexus types by resource key.

    def __lt__(self, other) -> bool:
        """ Nexus sort order is equivalent to that of their priority ints. """
        return self.PRIORITY < other.PRIORITY

    def check(self, pattern:str, **mode_kwargs) -> Optional[str]:
        """ Indicator function that returns a new pattern on success and can modify the current dict reference. """
        prefix = self.PREFIX
        if pattern.startswith(prefix):
            return pattern[len(prefix):]

    search = delegate_to("_d")
    lookup = delegate_to("_d")

    def command_args(self, match:str, mapping:object) -> Optional[tuple]:
        """ Return a tuple of items that can be directly called as an engine command to show a result, or None. """


use_if_resource_is = ResourceNexus.types


@use_if_resource_is("translations")
class TranslationNexus(ResourceNexus):
    """ A hybrid forward+reverse steno translation nexus. Used when nothing else matches. """

    PRIORITY = 1  # Has low priority. It must outrank the default nexus only.

    _forward: StripCaseSearchDict         # Forward translations dict (strokes -> English words).
    _reverse: ReverseStripCaseSearchDict  # Reverse translations dict (English words -> strokes).

    def __init__(self, d:Dict[str, str], strip:str=" -"):
        """ For translation-based searches, spaces and hyphens should be stripped off each end. """
        self._forward = StripCaseSearchDict(d, strip_chars=strip)
        self._reverse = ReverseStripCaseSearchDict(match=d, strip_chars=strip)

    def check(self, pattern:str, strokes:bool=False, **mode_kwargs) -> str:
        """ Indicator function that always returns success. Does not modify the pattern. """
        self._d = self._forward if strokes else self._reverse
        return pattern

    def command_args(self, match:str, mapping:object) -> tuple:
        """ The order of strokes/word in the lexer command is reversed for a reverse dict. """
        args = (match, mapping) if self._d is self._forward else (mapping, match)
        # We must send a lexer query to show a translation.
        if all(isinstance(i, str) for i in args):
            return ("lexer_query", *args)
        # If there is more than one of either input, make a product query to select the best combination.
        return ("lexer_query_product", *map(ensure_iterable, args))


@use_if_resource_is("rules")
class RulesNexus(ResourceNexus):
    """ A simple nexus for rule search by name when a prefix is added. There is only one dict, which never changes. """

    PRIORITY = 2  # Has medium priority. It must outrank the translations nexus.
    PREFIX = "/"  # A basic slash which is also a prefix of *other*, higher priority prefixes.

    def __init__(self, d:dict, strip:str=" .+-~"):
        """ To search the rules dictionary by name, prefix and suffix reference symbols should be stripped. """
        self._d = StripCaseSearchDict(d, strip_chars=strip)

    def command_args(self, match:str, mapping:object) -> tuple:
        """ If the mapping is a rule, send it as direct output just like the lexer would and return. """
        return "new_output", mapping


@use_if_resource_is("index")
class IndexNexus(ResourceNexus):
    """ A resource-heavy nexus for finding translations that contain a particular steno rule. """

    PRIORITY = 3      # Has highest priority but lowest chance of success. Must outrank the rules nexus.
    PREFIX = "//"     # This includes the rules prefix, so it must be checked first.
    DELIM: str = ";"  # Delimiter between rule name and translation.

    _index: Dict[str, dict]  # Index dict from which to create subnexus objects for any rule name on demand.
    _last_key: str = None    # Last valid rule key, to avoid creating a new search nexus on every query.
    _d: TranslationNexus     # Current nexus used to redirect checks and commands.

    def __init__(self, d:Dict[str, dict]):
        """ Index search is a two-part search. The first part goes by rule name, and is very precise.
            It is a key to generate translation nexus objects, so only exact matches will work. """
        self._index = d
        self._d = TranslationNexus({})

    def check(self, pattern:str, **mode_kwargs) -> Optional[str]:
        """ Indicator function for a rules search. Prefix is stripped by super method to get subnexus:pattern combo. """
        pattern = super().check(pattern)
        if pattern is not None:
            key, pattern = (pattern.split(self.DELIM, 1) + [""])[:2]
            if key in self._index:
                if key != self._last_key:
                    # Search dicts are memory hogs, and users tend to look at many results under the same rule.
                    # We generate each search nexus on demand only, and keep it until a new rule is requested.
                    self._last_key = key
                    self._d = TranslationNexus(self._index[key])
                return self._d.check(pattern, **mode_kwargs)

    search = delegate_to("_d", prefix=False)
    command_args = delegate_to("_d")

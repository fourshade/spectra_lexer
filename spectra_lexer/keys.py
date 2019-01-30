"""
There are two general string-based formats of steno keys:
StenoKeys - Each character is a unique key, lowercase letters used for right-side keys.
            Used by the lexer since one key is always one character with no possible
            ambiguity over sides even if the keys are in the wrong order.
RTFCRE - Keys are all uppercase, hyphen disambiguates left vs. right side of the board.
         Center keys may also delimit the sides, in which case the hyphen is omitted.
         Most steno dictionaries (i.e. for use in Plover) are in this format.
To differentiate between these, the first can be typed as StenoKeys and the latter as just str.
Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE.
"""

from collections import defaultdict
from typing import Callable, List, Tuple

from spectra_lexer.utils import str_map, str_prefix, str_without

# Key constants which aren't physical steno keys but appear in strings.
KEY_SEP = "/"
KEY_SPLIT = "-"
# Various ordered strings of keys for testing based on steno order.
L_KEYS = "#STKPWHR"
C_KEYS = "AO*EU"
R_KEYS = "frpblgtsdz"
# Various pre-computed key containers for fast membership testing.
C_KEYS_SET = set(C_KEYS)
C_KEYS_IN = C_KEYS_SET.intersection
IS_C_KEY = C_KEYS_SET.__contains__
# Number key and RTFCRE steno keys required to produce the numbers 0-9 in order with this key.
KEY_NUMBER = "#"
NUMBER_ALIASES = "OSTPHAFPLT"
NUMBER_LITERALS_IN = set(map(str, range(10))).intersection
# Translation table for cleansing steno strings of unknown origin.
VALID_CHAR_SET = set().union(L_KEYS, C_KEYS, R_KEYS, R_KEYS.upper(), KEY_SEP, KEY_SPLIT)
_TF_DICT = defaultdict(lambda: None, {ord(k): k for k in VALID_CHAR_SET})
_TF_DICT.update(enumerate(NUMBER_ALIASES, ord("0")))

# Public module-level function that works on any class of stroke.
join_strokes:Callable[[str], str] = KEY_SEP.join


class StenoKeys(str):
    """ Derived string class for a sequence of case-distinct steno keys with
        no hyphens and lowercase characters for every key on the right side. """

    def to_rtfcre(self) -> str:
        """ Transform a StenoKeys string to RTFCRE. Result will be a basic string. """
        return str_map(self, _stroke_stenokeys_to_rtfcre, KEY_SEP)

    @classmethod
    def from_rtfcre(cls, s:str):
        """ Transform a string from RTFCRE. Result will have the derived class.
            Overwrite the reverse method with one that returns the original string. """
        self = cls(str_map(s, _stroke_rtfcre_to_stenokeys, KEY_SEP))
        self.to_rtfcre = lambda: s
        return self

    @classmethod
    def cleanse_from_rtfcre(cls, s:str):
        """ Lexer input may come from the user, in which case the formatting cannot be trusted.
            Cleanse the string of abnormalities before parsing it as usual. """
        return cls.from_rtfcre(_cleanse_rtfcre(s))

    @classmethod
    def separator(cls):
        """ Return a class instance of the stroke separator. """
        return cls(KEY_SEP)

    def first_stroke(self) -> str:
        return str_prefix(self, KEY_SEP)

    def for_display(self) -> List[Tuple[str, bool]]:
        """ Generate a list of strokes along with whether or not they have been shifted with the number key. """
        return [(s, KEY_NUMBER in s) for s in self.split(KEY_SEP)]

    def has_separator(self) -> bool:
        """ Is there one or more stroke separators in the current key set? """
        return KEY_SEP in self

    def is_separator(self, index:int=None) -> bool:
        """ If no arguments, is the current key set only a stroke separator?
            With one argument, is the key at the given index a stroke separator? """
        return (self if index is None else self[index]) == KEY_SEP

    def without(self, keys:str):
        """ Return a copy of this object without each of the given keys (taken from the left). """
        if self.startswith(keys):
            return self.__class__(self[len(keys):])
        s = str_without(self, keys)
        return self.__class__(s)


def _stroke_stenokeys_to_rtfcre(s:str) -> str:
    """ Find the first right-side key (if there is one).
        If it doesn't follow a center key, insert a hyphen before it.
        Only uppercase the string if right-side keys exist."""
    for i, c in enumerate(s):
        if c in R_KEYS:
            if not i or s[i - 1] not in C_KEYS:
                s = s[:i] + KEY_SPLIT + s[i:]
            return s.upper()
    return s


def _stroke_rtfcre_to_stenokeys(s:str) -> str:
    """ Attempt to split each stroke into LC/R keys, either with a hyphen or the position of center keys. """
    # If there is a hyphen, split the string into left and right sides on it.
    if KEY_SPLIT in s:
        left, right = s.rsplit(KEY_SPLIT, 1)
        return _lowercase_right_and_join(left, right)
    # If there's no hyphen, we must search for the split point between C and R.
    # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
    # If there are no center keys, it is narrowed to L (left side only). No further modifications are necessary.
    if not C_KEYS_IN(s):
        return s
    # We are down to LC, LCR, CR as possible combinations.
    # The last center key in the string is the place to split, so start looking from the right end.
    c = next(filter(IS_C_KEY, reversed(s)))
    # Partition string to separate left/center keys from right keys.
    left, c, right = s.partition(c)
    return _lowercase_right_and_join(left + c, right)


def _lowercase_right_and_join(left:str, right:str) -> str:
    """ Rejoin string with right side lowercase. If there are no right side keys, just return the left. """
    return left + right.lower() if right else left


def _cleanse_rtfcre(s:str) -> str:
    """ A vigorous formatting operation for RTFCRE strings close to user operation.
        Remove all characters that are considered invalid in steno strings for the parser.
        Translate any literal numbers by replacing them with their key equivalents and adding
        a number key to the beginning of the stroke if one or more was replaced. """
    rep = s.translate(_TF_DICT)
    if rep != s and NUMBER_LITERALS_IN(s) and KEY_NUMBER not in s:
        rep = KEY_NUMBER + rep
    return rep

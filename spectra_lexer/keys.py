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

from typing import Callable, List, TypeVar

KEY_NUMBER = "#"

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


# Public module-level functions that work on any class of stroke.
join_strokes:Callable[[str], str] = KEY_SEP.join


def split_strokes(self:str) -> List[str]:
    """ Split a single string into a list by the stroke separator '/'  """
    return self.split(KEY_SEP)


def first_stroke(self) -> str:
    """ Return only the first stroke (or remnants thereof) as a standard string. """
    return self.split(KEY_SEP, 1)[0]


def has_separator(s:str) -> bool:
    """ Is there one or more stroke separators in the current key set? """
    return KEY_SEP in s


def is_separator(s, index:int=None) -> bool:
    """ If no arguments, is the current key set only a stroke separator?
        With one argument, is the key at the given index a stroke separator? """
    return (s if index is None else s[index]) == KEY_SEP


def is_number(s) -> bool:
    """ Is the current stroke a number of some form? """
    return KEY_NUMBER in s


T = TypeVar('StenoKeys')
class StenoKeys(str):
    """ Derived string class for a sequence of case-distinct steno keys with
        no hyphens and lowercase characters for every key on the right side. """

    def to_rtfcre(self) -> str:
        """ Transform a StenoKeys string to RTFCRE. Result will be a basic string. """
        return self.map_strokes(_stroke_stenokeys_to_rtfcre)

    @classmethod
    def from_rtfcre(cls, s:str) -> T:
        """ Transform a string from RTFCRE. Result will have the StenoKeys derived class. """
        return cls(cls.map_strokes(s, _stroke_rtfcre_to_stenokeys))

    def map_strokes(self:str, func:Callable[[str],str]) -> str:
        """ Split a steno key string into individual strokes, run a function on each of them,
            then join the return values back into one string with a stroke separator. """
        # If there are no stroke separators (i.e. one stroke), just run the function on that string and return it.
        if not has_separator(self):
            return func(self)
        # Otherwise, split on stroke separators, map, and re-join.
        strokes_iter = split_strokes(self)
        transformed = map(func, strokes_iter)
        return join_strokes(transformed)


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

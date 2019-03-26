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

from spectra_lexer.utils import nondata_property

# RTFCRE stroke delimiter. Separates individual strokes of a multi-stroke action.
KEY_SEP = "/"
# RTFCRE board split delimiter. Separates ambiguous strokes into left+center and right sides of the board.
KEY_SPLIT = "-"
# Special modifier key. This key does not respect steno order.
KEY_SPECIAL = "*"
# Unique characters for each key in steno order, moving left -> center -> right.
# Right keys are internally lowercased, so they may re-use characters from the left or center.
L_KEYS = "#STKPWHR"
C_KEYS = "AO*EU"
R_KEYS = "FRPBLGTSDZ"
# Some keys can be designated as shift keys. They will end up at the beginning of steno order when it matters.
# The number key is the main example. When held, keys mostly on the top row become numbers based on their position.
# These numbers are considered "aliases" for those keys in steno parsing. They are allowed to be present directly
# in RTFCRE key strings. This is a table of alias mappings for each shift key.
SHIFT_TABLE = {"#": {"0": "O", "1": "S", "2": "T", "3": "P", "4": "H",
                     "5": "A", "6": "F", "7": "P", "8": "L", "9": "T"}}

# Pre-computed key containers for fast membership testing.
_C_KEYS_SET = set(C_KEYS)
_R_KEYS_SET = set(R_KEYS.lower())
# Tables and functions for translating and cleansing RTFCRE steno strings of unknown origin.
_ALIASES_IN = {k for table in SHIFT_TABLE.values() for k in table}.intersection
_ALIAS_TABLE = {s: {ord(k): v for k, v in d.items()} for s, d in SHIFT_TABLE.items()}
_VALID_CHAR_SET = set().union(KEY_SEP, KEY_SPLIT, L_KEYS, C_KEYS, R_KEYS)
_VALID_TABLE = defaultdict(lambda: None, {ord(k): k for k in _VALID_CHAR_SET})


class StenoKeys(str):
    """ Derived string class for a sequence of case-distinct steno keys with
        no hyphens and lowercase characters for every key on the right side. """

    @nondata_property
    def strokes(self) -> list:
        """ Return every stroke in a StenoKeys object as a list of basic strings. """
        return self.split(KEY_SEP)

    @nondata_property
    def rtfcre(self) -> str:
        """ Transform a StenoKeys string to RTFCRE. Result will be a basic string. """
        return KEY_SEP.join(map(_stroke_stenokeys_to_rtfcre, self.strokes))

    @classmethod
    def from_rtfcre(cls, s:str):
        """ Transform a string from RTFCRE. Result will have the derived class.
            For performance, cache the stroke list and the original string on the instance. """
        strokes = list(map(_stroke_rtfcre_to_stenokeys, s.split(KEY_SEP)))
        self = cls(KEY_SEP.join(strokes))
        self.strokes = strokes
        self.rtfcre = s
        return self

    @classmethod
    def cleanse_from_rtfcre(cls, s:str):
        """ Lexer input may come from the user, in which case the formatting cannot be trusted.
            Cleanse the RTFCRE string of abnormalities before parsing it as usual. """
        if _ALIASES_IN(s):
            # Translate literal numbers by replacing them with their raw key equivalents and adding a number key.
            for k, d in _ALIAS_TABLE.items():
                rep = s.translate(d)
                if rep != s:
                    s = k + rep
        # Remove all characters that are considered invalid in steno strings and continue with RTFCRE parsing.
        s = s.translate(_VALID_TABLE)
        return cls.from_rtfcre(s)

    def __repr__(self) -> str:
        return repr(self.rtfcre)


def _stroke_stenokeys_to_rtfcre(s:str) -> str:
    """ Find the first right-side key (if there is one).
        If it doesn't follow a center key, insert a hyphen before it.
        Only uppercase the string if right-side keys exist. """
    for i, c in enumerate(s):
        if c in _R_KEYS_SET:
            if not i or s[i - 1] not in _C_KEYS_SET:
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
    # The last center key in the string (if any) is the place to split, so start looking from the right end.
    for c in reversed(s):
        if c in _C_KEYS_SET:
            # Partition string to separate left/center keys from right keys.
            left, c, right = s.partition(c)
            return _lowercase_right_and_join(left + c, right)
    # If there are no center keys, it is narrowed to L (left side only). No modifications are necessary.
    return s


def _lowercase_right_and_join(left:str, right:str) -> str:
    """ Rejoin string with right side lowercase. If there are no right side keys, just return the left. """
    return left + right.lower() if right else left

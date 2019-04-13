from collections import defaultdict
from functools import partial


class KeyLayout:
    """ There are two general string-based formats of steno keys:
    s-keys - Each key is a unique character. Lowercase letters are used for right-side keys.
             Used by the lexer since one key is always one character with no possible
             ambiguity over sides even if the keys are in the wrong order.
    RTFCRE - Keys are all uppercase, hyphen delimits left vs. right side of the board.
             Center keys may also delimit the sides, in which case the hyphen is omitted.
             Most steno dictionaries (i.e. for use in Plover) are in this format.
    String variables should be distinctly labeled as "skeys" when they use the first format.
    Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE. """

    # Stroke delimiter. Separates individual strokes of a multi-stroke action.
    SEP = "/"
    # RTFCRE board split delimiter. Separates ambiguous strokes into left+center and right sides of the board.
    SPLIT = "-"
    # Special modifier key. This key defies steno order to modify entire strokes.
    SPECIAL = "*"
    # Unique characters for each key in steno order, moving left -> center -> right.
    # Right keys are internally lowercased, so they may re-use letters (but not symbols) from the left or center.
    LEFT = "#STKPWHR"
    CENTER = "AO*EU"
    RIGHT = "FRPBLGTSDZ"
    # Some keys can be designated as shift keys. They will end up at the beginning of steno order when it matters.
    # The number key is the main example. When held, keys mostly on the top row become numbers based on their position.
    # These numbers are considered "aliases" for those keys in steno parsing. They are allowed to be present directly
    # in RTFCRE key strings. This is a table of alias mappings for each shift key.
    SHIFT_TABLE = {"#": {"0": "O", "1": "S", "2": "T", "3": "P", "4": "H",
                         "5": "A", "6": "F", "7": "P", "8": "L", "9": "T"}}

    def __init__(self, d:dict):
        """ Pre-compute character sets and tables for fast membership tests and string conversion. """
        self.__dict__.update(d)
        self._c_keys_set = set(self.CENTER)
        self._r_keys_set = set(self.RIGHT.lower())
        aliases = {k for table in self.SHIFT_TABLE.values() for k in table}
        self._aliases_in = aliases.intersection
        self._alias_table = {s: {ord(k): v for k, v in d.items()} for s, d in self.SHIFT_TABLE.items()}
        valid_chars = aliases.union(self.SEP, self.SPLIT, self.LEFT, self.CENTER, self.RIGHT)
        self._valid_table = defaultdict(type(None), {ord(k): k for k in valid_chars})
        # Create optimized map functions to convert every stroke in a string between forms.
        # Transform an s-keys string back to RTFCRE.
        self.to_rtfcre = partial(_stroke_map, self._stroke_s_keys_to_rtfcre, self.SEP)
        # Transform a string from RTFCRE to a sequence of case-distinct 's-keys'
        self.from_rtfcre = partial(_stroke_map, self._stroke_rtfcre_to_s_keys, self.SEP)

    def cleanse_from_rtfcre(self, s:str) -> str:
        """ Lexer input may come from the user, in which case the formatting cannot be trusted.
            Remove all characters that are considered invalid in steno strings before parsing it as usual. """
        return self.from_rtfcre(s.translate(self._valid_table))

    def _stroke_s_keys_to_rtfcre(self, s:str) -> str:
        """ Find the first right-side key (if there is one).
            If it doesn't follow a center key, insert a hyphen before it.
            Only uppercase the string if right-side keys exist. """
        for i, c in enumerate(s):
            if c in self._r_keys_set:
                if not i or s[i - 1] not in self._c_keys_set:
                    s = s[:i] + self.SPLIT + s[i:]
                return s.upper()
        return s

    def _stroke_rtfcre_to_s_keys(self, s:str) -> str:
        """ Perform alias substitution, split each stroke into left and right sides, and convert the case. """
        if self._aliases_in(s):
            # Translate literal numbers by replacing them with their raw key equivalents and adding a number key.
            for k, d in self._alias_table.items():
                rep = s.translate(d)
                if rep != s:
                    s = k + rep
        # Attempt to split each stroke into LC/R keys, If there's a hyphen, split the string there.
        if self.SPLIT in s:
            left, right = s.rsplit(self.SPLIT, 1)
            return _lowercase_right_and_join(left, right)
        # If there's no hyphen, we must search for the split point between C and R.
        # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
        # The last center key in the string (if any) is the place to split, so start looking from the right end.
        for c in reversed(s):
            if c in self._c_keys_set:
                # Partition string to separate left/center keys from right keys.
                left, c, right = s.partition(c)
                return _lowercase_right_and_join(left + c, right)
        # If there are no center keys, it is narrowed to L (left side only). No modifications are necessary.
        return s


def _lowercase_right_and_join(left:str, right:str) -> str:
    """ Rejoin string with right side lowercase. If there are no right side keys, just return the left. """
    return left + right.lower() if right else left


def _stroke_map(fn, sep, s:str, _split=str.split) -> str:
    """ Split a set of keys, apply a string function to every stroke, and join them back together.
        If there is only one stroke, skip the string carving and apply the function directly. """
    if sep in s:
        return sep.join(map(fn, _split(s, sep)))
    return fn(s)

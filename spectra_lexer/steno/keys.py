from functools import partial
from typing import Callable


class KeyLayout:
    """ Contains all sections and characters required in a standard steno key layout.

    There are two general string-based formats of steno keys:
    s-keys - Each key is a unique character. Lowercase letters are used for right-side keys.
             Used by the lexer since one key is always one character with no possible
             ambiguity over sides even if the keys are in the wrong order.
    RTFCRE - Keys are all uppercase, hyphen delimits left vs. right side of the board.
             Center keys may also delimit the sides, in which case the hyphen is omitted.
             Most steno dictionaries (i.e. for use in Plover) are in this format.
    String variables should be distinctly labeled as "skeys" when they use the first format.
    Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE. """

    # Stroke delimiter. Separates individual strokes of a multi-stroke action.
    sep = "/"
    # RTFCRE board split delimiter. Separates ambiguous strokes into left+center and right sides of the board.
    split = "-"
    # Unique characters for each key in steno order, moving left -> center -> right.
    # Right keys are internally lowercased, so they may re-use letters (but not symbols) from the left or center.
    left = "#STKPWHR"
    center = "AO*EU"
    right = "FRPBLGTSDZ"
    # The special key is used in hardcoded disambiguation rules.
    special = "*"
    # Some keys may ignore steno order. This has a large performance and accuracy cost.
    # Only the asterisk is typically used in such a way that this treatment is worth it.
    unordered = "*"
    # Some keys can be designated as shift keys. They will end up at the beginning of steno order when it matters.
    # The number key is the main example. When held, keys mostly on the top row become numbers based on their position.
    # These numbers are considered "aliases" for those keys in steno parsing. They are allowed to be present directly
    # in RTFCRE key strings. This is a table of aliases mapped to strings with two characters: "shift_key, real_key".
    aliases = {"0": "#O", "1": "#S", "2": "#T", "3": "#P", "4": "#H",
               "5": "#A", "6": "#F", "7": "#P", "8": "#L", "9": "#T"}

    def __init__(self, **kwargs) -> None:
        """ Start with the constructor kwargs as instance attributes.
            Pre-compute character sets, tables, and functions for fast membership tests and string conversion. """
        self.__dict__ = kwargs
        self._c_keys_set = frozenset(self.center)
        self._r_keys_set = frozenset(self.right.lower())
        self._valid_rtfcre = {self.sep, self.split, *self.left, *self.center, *self.right}
        # Create optimized partial map functions to apply string operations to every stroke in a key string.
        # Transform a string from RTFCRE to a sequence of case-distinct 's-keys'.
        self.from_rtfcre = partial(self._stroke_map, self._stroke_rtfcre_to_s_keys)
        # Transform an s-keys string back to RTFCRE.
        self.to_rtfcre = partial(self._stroke_map, self._stroke_s_keys_to_rtfcre)

    def _stroke_map(self, fn:Callable[[str], str], s:str) -> str:
        """ Split a set of keys, apply a string function to every stroke, and join them back together.
            If there is only one stroke, skip the string carving and apply the function directly. """
        sep = self.sep
        if sep in s:
            return sep.join(map(fn, s.split(sep)))
        return fn(s)

    def _stroke_rtfcre_to_s_keys(self, s:str) -> str:
        """ Translate an RTFCRE stroke into s-keys format. """
        for k in s:
            if k not in self._valid_rtfcre:
                s = self._replace_rtfcre(s, k)
        # Attempt to split each stroke into LC/R keys.
        # If there's a hyphen, split the string there and rejoin with right side lowercase.
        if self.split in s:
            left, right = s.rsplit(self.split, 1)
            return left + right.lower()
        # If there's no hyphen, we must search for the split point between C and R.
        # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
        # The last center key in the string (if any) is the place to split, so start looking from the right end.
        for c in reversed(s):
            if c in self._c_keys_set:
                # Partition string to separate left/center keys from right keys.
                left, c, right = s.rpartition(c)
                left += c
                return left + right.lower()
        # If there are no center keys, it is narrowed to L (left side only). No modifications are necessary.
        return s

    def _replace_rtfcre(self, s:str, alias_key:str) -> str:
        """ Translate a literal number or other alias by replacing it with its raw key equivalent.
            If it requires a shift key/number key, add it to the start of the string if not present. """
        try:
            shift_key, real_key = self.aliases[alias_key]
            if shift_key not in s:
                s = shift_key + s
        except KeyError:
            # If the character is completely invalid, remove it.
            real_key = ""
        return s.replace(alias_key, real_key)

    def _stroke_s_keys_to_rtfcre(self, s:str) -> str:
        """ Find the first right-side key in the stroke (if there is one).
            If it doesn't follow a center key, insert a hyphen before it.
            Only uppercase the string if right-side keys exist.
            This is idempotent; it will do nothing if the input is already RTFCRE. """
        for i, c in enumerate(s):
            if c in self._r_keys_set:
                if not i or s[i - 1] not in self._c_keys_set:
                    s = s[:i] + self.split + s[i:]
                return s.upper()
        return s

    def verify(self) -> None:
        """ Test various properties of the layout for correctness. """
        # There cannot be duplicate keys within a side.
        sides = [self.left, self.center, self.right]
        left, center, right = sets = list(map(set, sides))
        assert sum(map(len, sets)) == sum(map(len, sides))
        # The center keys must not share any characters with the sides.
        assert center.isdisjoint(left | right)
        # The left and right sides must not share characters after casing.
        assert left.isdisjoint(map(str.lower, right))
        # The divider keys must not duplicate normal keys.
        normal_key_set = left | center | right
        assert self.sep not in normal_key_set
        assert self.split not in normal_key_set
        # The special key, unordered keys, and alias values must be normal keys previously defined.
        assert {self.special}.union(self.unordered, *self.aliases.values()) <= normal_key_set

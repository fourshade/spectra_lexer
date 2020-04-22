from typing import Callable, Dict, Set


class StenoKeyConverter:
    """ Converter between two general string-based formats of steno keys:
        s-keys - Each key is a unique character. Lowercase letters are used for right-side keys.
                 Used by the lexer since one key is always one character with no possible
                 ambiguity over sides even if the keys are in the wrong order.
        RTFCRE - Keys are all uppercase, hyphen delimits left vs. right side of the board.
                 Center keys may also delimit the sides, in which case the hyphen is omitted.
                 Most steno dictionaries (i.e. for use in Plover) are in this format.
        String variables should be distinctly labeled as "skeys" when they use the first format.
        Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE. """

    def __init__(self, key_sep:str, key_split:str, alias_table:Dict[str, str],
                 valid_rtfcre:Set[str], center_keys:Set[str], right_skeys:Set[str]) -> None:
        self._key_sep = key_sep            # Stroke delimiter. Separates individual strokes of a multi-stroke action.
        self._key_split = key_split        # RTFCRE board split delimiter.
        self._alias_table = alias_table    # Table of aliases mapped to two-character strings: "shift_key, real_key".
        self._valid_rtfcre = valid_rtfcre  # Set of all characters valid in an RTFCRE string.
        self._center_keys = center_keys    # Set of all center keys, which are the same in either format.
        self._right_skeys = right_skeys    # Set of all right-side s-keys.

    def rtfcre_to_skeys(self, s:str) -> str:
        """ Transform an RTFCRE steno key string to s-keys. """
        return self._stroke_map(s, self._stroke_rtfcre_to_skeys)

    def skeys_to_rtfcre(self, s:str) -> str:
        """ Transform an s-keys string back to RTFCRE. """
        return self._stroke_map(s, self._stroke_skeys_to_rtfcre)

    def _stroke_map(self, s:str, fn:Callable[[str], str]) -> str:
        """ Split a set of keys, apply a string function to every stroke, and join them back together.
            If there is only one stroke, skip the string carving and apply the function directly. """
        sep = self._key_sep
        if sep in s:
            return sep.join(map(fn, s.split(sep)))
        return fn(s)

    def _stroke_rtfcre_to_skeys(self, s:str) -> str:
        """ Translate an RTFCRE stroke into s-keys format. """
        for k in s:
            if k not in self._valid_rtfcre:
                s = self._replace_rtfcre(s, k)
        # Attempt to split each stroke into LC/R keys.
        # If there's a hyphen, split the string there and rejoin with right side lowercase.
        if self._key_split in s:
            left, right = s.rsplit(self._key_split, 1)
            return left + right.lower()
        # If there's no hyphen, we must search for the split point between C and R.
        # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
        # The last center key in the string (if any) is the place to split, so start looking from the right end.
        for k in reversed(s):
            if k in self._center_keys:
                left, right = s.rsplit(k, 1)
                return left + k + right.lower()
        # If there are no center keys, it is narrowed to L (left side only). No modifications are necessary.
        return s

    def _replace_rtfcre(self, s:str, alias_key:str) -> str:
        """ Translate a literal number or other alias by replacing it with its raw key equivalent.
            If it requires a shift key/number key, add it to the start of the string if not present. """
        try:
            shift_key, real_key = self._alias_table[alias_key]
            if shift_key not in s:
                s = shift_key + s
        except KeyError:
            # If the character is completely invalid, remove it.
            real_key = ""
        return s.replace(alias_key, real_key)

    def _stroke_skeys_to_rtfcre(self, s:str) -> str:
        """ Find the first right-side key in the stroke (if there is one).
            If it doesn't follow a center key, insert a hyphen before it.
            Only uppercase the string if right-side keys exist.
            This is idempotent; it will do nothing if the input is already RTFCRE. """
        for i, k in enumerate(s):
            if k in self._right_skeys:
                if not i or s[i - 1] not in self._center_keys:
                    s = s[:i] + self._key_split + s[i:]
                return s.upper()
        return s


class StenoKeyLayout:
    """ Contains all sections and characters required in a standard steno key layout. """

    # Stroke delimiter. Separates individual strokes of a multi-stroke action.
    sep = "/"
    # RTFCRE board split delimiter. Separates ambiguous strokes into left+center and right sides of the board.
    split = "-"
    # Unique characters for each key in steno order, moving left -> center -> right.
    # Right keys are internally lowercased, so they may re-use letters (but not symbols) from the left or center.
    left = "#STKPWHR"
    center = "AO*EU"
    right = "FRPBLGTSDZ"
    # Some keys may ignore steno order. This has a large performance and accuracy cost.
    # Only the asterisk is typically used in such a way that this treatment is worth it.
    unordered = "*"
    # Some keys can be designated as shift keys. They will end up at the beginning of steno order when it matters.
    # The number key is the main example. When held, keys mostly on the top row become numbers based on their position.
    # These numbers are considered "aliases" for those keys in steno parsing. They are allowed to be present directly
    # in RTFCRE key strings. This is a table of aliases mapped to strings with two characters: "shift_key, real_key".
    aliases = {"0": "#O", "1": "#S", "2": "#T", "3": "#P", "4": "#H",
               "5": "#A", "6": "#F", "7": "#P", "8": "#L", "9": "#T"}

    @classmethod
    def from_dict(cls, d:dict) -> "StenoKeyLayout":
        """ Return a layout parsed from a standard dict. """
        self = cls()
        self.__dict__.update(d)
        return self

    def dividers(self) -> Set[str]:
        """ Return the set of valid characters used as delimiters rather than physical steno keys. """
        return {self.sep, self.split}

    def valid_rtfcre(self) -> Set[str]:
        """ Return the set of all characters that are valid in a standard RTFCRE string. """
        return self.dividers().union(self.left, self.center, self.right)

    def verify(self) -> None:
        """ Test various properties of the layout for correctness. """
        # There cannot be duplicate keys within a side.
        sides = [self.left, self.center, self.right]
        for s in sides:
            assert len(s) == len(set(s))
        # The center keys must not share any characters with the sides.
        left, center, right = map(set, sides)
        assert center.isdisjoint(left | right)
        # The left and right sides must not share characters after casing.
        assert left.isdisjoint(self.right.lower())
        # The unordered keys must be normal keys previously defined.
        normal_key_set = left | center | right
        assert set(self.unordered) <= normal_key_set
        # The divider keys must *not* be normal keys.
        assert self.dividers().isdisjoint(normal_key_set)
        # Aliases must consist of single keys mapped to pairs of normal keys.
        for k, v in self.aliases.items():
            assert len(k) == 1
            assert len(v) == 2
            assert set(v) <= normal_key_set

    def make_parser(self) -> StenoKeyConverter:
        """ Pre-compute character sets for fast membership tests and string conversion. """
        valid_rtfcre = self.valid_rtfcre()
        center_keys = set(self.center)
        right_skeys = set(self.right.lower())
        return StenoKeyConverter(self.sep, self.split, self.aliases, valid_rtfcre, center_keys, right_skeys)

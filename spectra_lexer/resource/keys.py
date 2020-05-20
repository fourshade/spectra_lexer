from typing import AbstractSet, Callable, Dict


class StenoKeyLayout:
    """ Contains all sections and characters required in a standard steno key layout.
        There are two general string-based formats of steno keys:
        s-keys - Internal format used exclusively by this application.
                 Each key is a unique character. Lowercase letters are used for right-side keys.
                 Used by the lexer since one key is always one character with no possible
                 ambiguity over sides even if the keys are in the wrong order.
        RTFCRE - Older format defined in the "RTF Court Reporting Extensions" specification.
                 Keys are all uppercase, hyphen delimits left vs. right side of the board.
                 Center keys may also delimit the sides, in which case the hyphen is omitted.
                 Most steno dictionaries (i.e. for use in Plover) have strokes in this format.
        String variables should be distinctly labeled as "skeys" when they use the first format.
        Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE. """

    def __init__(self, *, sep:str, split:str, left:str, center:str, right:str,
                 special:str, aliases:Dict[str, str], **unused) -> None:
        self._sep = sep          # Stroke delimiter. This is the same in either format.
        self._split = split      # RTFCRE board split delimiter.
        self._special = special  # A single special-cased s-key (the asterisk).
        self._aliases = aliases  # Table of aliases mapped to two-character strings: "shift_key, real_key".
        # Save some fields as pre-computed (immutable) sets for fast membership tests and string conversion.
        self._left_set = frozenset(left)              # Left-side keys. These are the same in either format.
        self._center_set = frozenset(center)          # Center keys. These are the same in either format.
        self._right_set = frozenset(right)            # Right-side RTFCRE keys.
        self._right_skeys = frozenset(right.lower())  # Right-side s-keys.
        self._valid_rtfcre = frozenset({sep, split, *left, *center, *right})

    def separator_key(self) -> str:
        return self._sep

    def divider_key(self) -> str:
        return self._split

    def special_key(self) -> str:
        return self._special

    def valid_rtfcre(self) -> AbstractSet[str]:
        """ Return the set of all characters that are valid in a standard RTFCRE string. """
        return self._valid_rtfcre

    def rtfcre_to_skeys(self, s:str) -> str:
        """ Transform an RTFCRE steno key string to s-keys. """
        return self._stroke_map(s, self._stroke_rtfcre_to_skeys)

    def skeys_to_rtfcre(self, s:str) -> str:
        """ Transform an s-keys string back to RTFCRE. """
        return self._stroke_map(s, self._stroke_skeys_to_rtfcre)

    def _stroke_map(self, s:str, fn:Callable[[str], str]) -> str:
        """ Split a set of keys, apply a string function to every stroke, and join them back together.
            If there is only one stroke, skip the string carving and apply the function directly. """
        sep = self._sep
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
        if self._split in s:
            left, right = s.rsplit(self._split, 1)
            return left + right.lower()
        # If there's no hyphen, we must search for the split point between C and R.
        # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
        # The last center key in the string (if any) is the place to split, so start looking from the right end.
        for k in reversed(s):
            if k in self._center_set:
                left, right = s.rsplit(k, 1)
                return left + k + right.lower()
        # If there are no center keys, it is narrowed to L (left side only). No modifications are necessary.
        return s

    def _replace_rtfcre(self, s:str, alias_key:str) -> str:
        """ Translate a literal number or other alias by replacing it with its raw key equivalent.
            If it requires a shift key/number key, add it to the start of the string if not present. """
        try:
            shift_key, real_key = self._aliases[alias_key]
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
                if not i or s[i - 1] not in self._center_set:
                    s = s[:i] + self._split + s[i:]
                return s.upper()
        return s

    def verify(self) -> None:
        """ Test various properties of the layout for correctness. """
        left = self._left_set
        center = self._center_set
        right = self._right_set
        normal_key_set = left | center | right
        # The center keys must not share any characters with the sides.
        assert not center & left
        assert not center & right
        # The left and right sides must not share characters after casing.
        assert not left & self._right_skeys
        # The special key must be a normal key previously defined.
        assert self._special in normal_key_set
        # The delimiters must *not* be previously defined keys.
        assert self._sep not in normal_key_set
        assert self._split not in normal_key_set
        # Aliases must consist of single keys mapped to pairs of normal keys.
        for k, v in self._aliases.items():
            assert len(k) == 1
            assert len(v) == 2
            assert set(v) <= normal_key_set

    @classmethod
    def from_json_dict(cls, d:dict) -> "StenoKeyLayout":
        """ Create a layout from a JSON dict unpacked as **kwargs. """
        try:
            return cls(**d)
        except TypeError as e:
            raise TypeError("Key layout definitions are incomplete") from e

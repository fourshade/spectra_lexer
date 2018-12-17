from collections import defaultdict
from operator import methodcaller

# Key constant definitions; includes the separator and hyphen, which aren't physical steno keys but appear in strings.
KEY_SEP = "/"
KEY_SPLIT = "-"
KEY_STAR = "*"
KEY_NUMBER = "#"

# Various ordered strings of keys for testing based on steno order.
L_KEYS = "#STKPWHR"
C_KEYS = "AO*EU"
R_KEYS = "frpblgtsdz"
LC_KEYS = L_KEYS + C_KEYS
ALL_KEYS = LC_KEYS + R_KEYS

# Various sets of keys for fast membership testing.
C_KEYS_SET = set(C_KEYS)
VALID_CHAR_SET = set(ALL_KEYS + R_KEYS.upper() + KEY_SEP + KEY_SPLIT)

# Steno keys required to produce the numbers 0-9 in order (with the number key).
NUMBER_ALIASES = "OSTPHAfplt"

# Translation tables for cleansing steno strings of unknown origin.
NUM_TF_DICT = dict(enumerate(NUMBER_ALIASES, ord("0")))
VALID_TF_DICT = defaultdict(lambda: None, {ord(k): k for k in VALID_CHAR_SET})

# Exportable methods for joining and splitting strokes by "/"
join_strokes = KEY_SEP.join
split_strokes = methodcaller("split", KEY_SEP)


class StenoKeys(str):
    """
    Container class for a sequence of steno keys, with the full key string as the base object.

    There are two general string-based formats of steno keys:
    StenoKeys - Each character is a unique key, lowercase letters used for right-side keys.
                Used by the lexer since one key is always one character with no possible
                ambiguity over sides even if the keys are in the wrong order.
    RTFCRE - Keys are all uppercase, hyphen disambiguates left vs. right side of the board.
             Most steno dictionaries (i.e. for use in Plover) are in this format.
    To differentiate between these, the first can be typed as StenoKeys and the latter just as str.
    Characters from an outside source (JSON files or the Plover engine) are assumed to be RTFCRE.
    """

    def inv_parse(self) -> str:
        """ Perform the opposite of a standard parse to get the keys back into
            RTFCRE format with all uppercase letters and maybe a hyphen. """
        s_list = []
        # Iterate over all strokes (may only be 1).
        for s in split_strokes(self):
            # Find the first right-hand key (if there is one).
            # If it doesn't follow a center key, it needs a hyphen before it.
            # Whatever happens, join everything back together at the end.
            c_list = list(s)
            prev = None
            for i, c in enumerate(c_list):
                if c in R_KEYS:
                    if prev is None or prev not in C_KEYS:
                        c_list.insert(i, KEY_SPLIT)
                    break
                prev = c
            s_list.append("".join(c_list).upper())
        # Join everything back together with stroke separators.
        return join_strokes(s_list)

    @classmethod
    def parse(cls, key_str:str) -> __qualname__:
        """ Parse a standard RTFCRE key string and return a key sequence with
            no hyphens and lowercase characters for every key on the right side. """
        s_list = []
        # Iterate over all strokes (may only be 1) and attempt to split each string into LC/R keys.
        for s in split_strokes(key_str):
            s_set = set(s)
            if KEY_SPLIT in s_set:
                # If there is a hyphen (KEY_SPLIT), we know exactly where to split the string.
                # Lowercase the right side, rejoin the string, and add it to the list.
                lc, r = s.split(KEY_SPLIT, 1)
                s_list.append(lc + r.lower())
            else:
                # If there's not a hyphen, we must find the split point.
                # First find out what center keys we have. Allowable combinations up to here are L, LC, LCR, CR.
                c_set = s_set & C_KEYS_SET
                if c_set:
                    # The last center key in the string is the place to split.
                    for c in reversed(s):
                        if c in c_set:
                            # Partition and rejoin string with right side lowercase if needed, then add it to the list.
                            *lc, r = s.partition(c)
                            s_list.append("".join((*lc, r.lower())) if r else s)
                            break
                else:
                    # All keys must be on the left side. No need to modify the stroke; just add it to the list.
                    s_list.append(s)
        # Join everything back together with stroke separators and create a new keys object.
        return cls(join_strokes(s_list))

    @classmethod
    def cleanse(cls, key_str:str) -> __qualname__:
        """
        A more vigorous formatting operation for RTFCRE strings closer to user operation.
        Remove all characters that are considered invalid in steno strings for the parser.
        Translate any literal numbers by replacing them with their key equivalents and adding
        a number key to the beginning of the stroke if one or more was replaced.
        """
        s_list = []
        for s in split_strokes(key_str):
            # An empty stroke is invalid. It will be skipped entirely.
            if s:
                # Replace numbers with keys. If we replaced some, add a number key (if there isn't one).
                num_rep = s.translate(NUM_TF_DICT)
                if num_rep != s and KEY_NUMBER not in s:
                    num_rep = KEY_NUMBER + num_rep
                # Remove all invalid keys from the string and add it to the clean list.
                valid_keys = num_rep.translate(VALID_TF_DICT)
                s_list.append(valid_keys)
        # Rejoin the string and do a regular parse to eliminate hyphens and the like.
        return cls.parse(join_strokes(s_list))

from spectra_lexer.keys import KEY_SEP, KEY_STAR, StenoKeys

# Steno order is not enforced for any keys in this set. This has a large performance and accuracy cost.
# Only the asterisk is used in such a way that this treatment is worth it.
UNORDERED_KEYS = {KEY_STAR}
UNORDERED_KEYS_IN = UNORDERED_KEYS.intersection


class LexerKeys(StenoKeys):
    """ Special subclass of StenoKeys with copy-and-mutate methods for active use by the lexer.
        Tracks "ordered" and "unordered" keys independently of the full set in the base string. """

    ordered: str    # Ordered string of normal keys that must be consumed starting from the left.
    unordered: set  # Unordered keys (asterisk) in the current stroke that may be consumed at any time.

    def __new__(cls, key_seq:str) -> __qualname__:
        """ Create the base string with all keys, then use that to start an ordered copy.
            Filter the unordered keys out of that and save it for use as a dict key.
            Keys must already be in dehyphenated, case-distinct format."""
        self = super().__new__(cls, key_seq)
        unordered = UNORDERED_KEYS_IN(key_seq)
        if unordered:
            unordered = UNORDERED_KEYS_IN(key_seq.split(KEY_SEP, 1)[0])
            for k in unordered:
                key_seq = key_seq.replace(k, "", 1)
        self.ordered = key_seq
        self.unordered = unordered
        return self

    def without(self, keys:str) -> __qualname__:
        """ Return a copy of this key sequence object without each of the given keys (taken from the left). """
        if self.startswith(keys):
            return LexerKeys(self[len(keys):])
        for k in keys:
            self = self.replace(k, "", 1)
        return LexerKeys(self)

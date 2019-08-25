from collections import namedtuple
from typing import Dict, List, Sequence

from ..keys import KeyLayout
from ..rules import RuleFlags, StenoRule


class LexerMatch(namedtuple("LexerMatch", "rule skeys letters skeys_len letters_len")):
    """ Container for a steno rule match with s-keys. """
    # rule: StenoRule   - Original immutable rule.
    # skeys: str        - Lexer-formatted steno keys that make up the rule.
    # letters: str      - Raw English text of the word.
    # skeys_len: int    - Length of <skeys>.
    # letters_len: int  - Length of <letters>.

    @classmethod
    def new(cls, r:StenoRule, skeys:str, letters:str):
        """ Create a match object with precalculated lengths for speed. """
        return cls(r, skeys, letters, len(skeys), len(letters))

    @classmethod
    def special(cls, skeys:str, desc:str):
        """ Create a special (no-letter) rule and place it in a match object. """
        return cls(StenoRule(skeys, "", RuleFlags(), desc, ()), skeys, "", len(skeys), 0)


class SpecialRuleFinder:
    """ Dictionary for "special" rules, including built-in rules not loaded from JSON. """
    # Identifiers for special rules that are handled individually in code.
    CONFLICT = "CF"
    PROPER = "PR"
    ABBREVIATION = "AB"
    AFFIX = "PS"
    FINGERSPELL = "FS"
    OBSCENE = "OB"

    _d: Dict[str, LexerMatch]  # Contains rules that match by reference name.
    _key_sep: str              # Steno key used as stroke separator in both stroke formats.
    _key_star: str             # Steno key used for special translation-wide matches.
    _rule_sep: LexerMatch      # Separator rule constant.
    _rule_unknown: LexerMatch  # Unknown special rule constant.

    def __init__(self, d:Dict[str, LexerMatch], sep:str, star:str) -> None:
        self._d = d
        self._key_sep = sep
        self._key_star = star
        # The separator rule constant is specifically matched on its own.
        self._rule_sep = LexerMatch.special(sep, "Stroke separator")
        # The unknown special rule constant is required in case no special rules match (or a matched rule is missing).
        self._rule_unknown = LexerMatch.special(star, "purpose unknown\nPossibly resolves a conflict")

    def __call__(self, skeys_fs:str, skeys:str, all_skeys:str, all_letters:str) -> LexerMatch:
        """ Check the first stroke for special rules. Return the first one if there are any. """
        # If our current stroke is empty, a stroke separator is next. Return its rule.
        if not skeys_fs:
            return self._rule_sep
        # If we only have a star left at the end of a stroke, try to guess its meaning.
        # If execution reaches the end without a valid guess, return the "ambiguous" rule.
        if skeys_fs == self._key_star:
            rule_type = self._analyze_star(skeys, all_skeys, all_letters)
            return self._d.get(f"{self._key_star}:{rule_type}") or self._rule_unknown

    def _analyze_star(self, skeys:str, all_skeys:str, all_letters:str) -> str:
        """ Try to guess the meaning of an asterisk from the remaining keys, the full set of keys,
            the full word, and the current rulemap. Return the reference type for the best-guess rule (if any). """
        # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
        if "." in all_letters:
            return self.ABBREVIATION
        # If the word has uppercase letters in it, it's probably a proper noun.
        if all_letters != all_letters.lower():
            return self.PROPER
        # If we have a multi-stroke word and are at the beginning or end of it, it's probably a prefix or suffix.
        splits_left, all_splits = skeys.count(self._key_sep), all_skeys.count(self._key_sep)
        if all_splits and (not splits_left or splits_left == all_splits):
            return self.AFFIX


class PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _root: dict  # Root node of the tree. Matches the empty sequence, which is a prefix of everything.

    def __init__(self) -> None:
        self._root = {"values": []}

    def __setitem__(self, k:Sequence, v:object) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        node = self._root
        for element in k:
            node = node.get(element) or node.setdefault(element, {"values": []})
        node["values"].append(v)

    def compile(self) -> None:
        """ Finalize the tree by populating nodes with values from all possible prefixes.
            Must be called before use. Invalidated by modification. """
        self._compile(self._root, [])

    def _compile(self, node:dict, values:list) -> None:
        v = node.pop("values")
        v += values
        for n in node.values():
            self._compile(n, v)
        node["values"] = v

    def __getitem__(self, k:Sequence) -> list:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from longest prefix matched to shortest. """
        node = self._root
        for element in k:
            if element not in node:
                break
            node = node[element]
        return node["values"]


class PrefixFinder:
    """ Search engine that finds rules matching a prefix of steno-ordered keys.
        Steno order may also be ignored for certain keys. This has a large performance and accuracy cost.
        Only the asterisk is used in such a way that this treatment is worth it. """

    _tree: PrefixTree    # Primary search tree.
    _key_sep: str        # Steno key used as stroke separator.
    _unordered_key: str  # Key to put into unordered set.

    def __init__(self, items:Sequence[LexerMatch], sep:str, unordered_key:str) -> None:
        """ Make the tree and the filter that returns which keys will be and won't be tested in prefixes.
            Separate the given sets of keys into ordered keys (which contain any prefix) and unordered keys.
            Index the rules, letters, and unordered keys under the ordered keys and compile the tree. """
        tree = self._tree = PrefixTree()
        self._key_sep = sep
        self._unordered_key = unordered_key
        for r in items:
            ordered, unordered = self._unordered_filter(r.skeys)
            tree[ordered] = (r, r.letters, unordered)
        tree.compile()

    def __call__(self, skeys:str, letters:str) -> list:
        """ Return a list of all rules that match a prefix of the given ordered keys,
            a subset of the given letters, and a subset of the given unordered keys. """
        ordered, unordered = self._unordered_filter(skeys)
        return [r for (r, rl, ru) in self._tree[ordered] if rl in letters and ru <= unordered]

    def _unordered_filter(self, skeys:str, _empty=frozenset()) -> tuple:
        """ Filter out asterisks in the first stroke that may be consumed at any time and return them.
            Also return the remaining ordered keys that must be consumed starting from the left. """
        star = self._unordered_key
        if (star not in skeys) or (star not in skeys.split(self._key_sep, 1)[0]):
            return skeys, _empty
        return skeys.replace(star, ""), frozenset([star])


class LexerRuleMatcher:
    """ A master dictionary of steno rules. Each component dict maps strings to steno rules in some way. """

    _key_sep: str  # Steno key used as stroke separator in both stroke formats.

    _special_finder: SpecialRuleFinder     # Rules that match by reference name.
    _stroke_dict: Dict[str, LexerMatch]  # Rules that match by full stroke only.
    _word_dict: Dict[str, LexerMatch]    # Rules that match by exact word only (whitespace-separated).
    _prefix_finder: PrefixFinder         # Rules that match by starting with certain keys in order.

    def __init__(self, layout:KeyLayout, rules:Dict[str, StenoRule]) -> None:
        """ Construct constants and a specially-structured series of dictionaries from a steno system. """
        self._key_sep = sep = layout.SEP
        star = layout.SPECIAL
        from_rtfcre = layout.from_rtfcre
        special_entries = {}
        stroke_dict = {}
        word_dict = {}
        prefix_entries = []
        # Sort rules into specific dictionaries based on specific flags for the lexer matching system.
        match_name = RuleFlags.SPECIAL
        match_stroke = RuleFlags.STROKE
        match_word = RuleFlags.WORD
        for n, r in rules.items():
            # All rules must have their keys parsed into the case-unique s-keys format.
            skeys = from_rtfcre(r.keys)
            letters = r.letters
            flags = r.flags
            lr = LexerMatch.new(r, skeys, letters)
            # Internal rules are only used in special cases, by name.
            if match_name in flags:
                special_entries[n] = lr
            # Filter stroke and word rules into their own dicts.
            elif match_stroke in flags:
                stroke_dict[skeys] = lr
            elif match_word in flags:
                word_dict[letters] = lr
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                prefix_entries.append(lr)
        self._special_finder = SpecialRuleFinder(special_entries, sep, star)
        self._stroke_dict = stroke_dict
        self._word_dict = word_dict
        self._prefix_finder = PrefixFinder(prefix_entries, sep, star)

    def __call__(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[LexerMatch]:
        """ Return a list of rules that match the given keys and letters in any of the dictionaries. """
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        # For special single-key end-cases, there are no better matches, so return immediately if one is found.
        special_rule = self._special_finder(skeys_fs, skeys, all_skeys, all_letters)
        if special_rule is not None:
            return [special_rule]
        # Try to match keys by prefix. This may yield a large number of rules.
        matches = self._prefix_finder(skeys, letters)
        # We have a complete stroke next if we just started or a stroke separator was just matched.
        is_start = (skeys == all_skeys)
        if is_start or all_skeys[-len(skeys) - 1] == self._key_sep:
            # For the stroke dictionary, the rule must match the next full stroke and a subset of the given letters.
            stroke_rule = self._stroke_dict.get(skeys_fs)
            if stroke_rule and stroke_rule.letters in letters:
                matches.append(stroke_rule)
        # We have a complete word if we just started or the word pointer is sitting on a space.
        if is_start or letters[:1] == ' ':
            # For the word dictionary, the rule must match a prefix of the given keys and the next full word.
            words = letters.split()
            if words:
                word_rule = self._word_dict.get(words[0])
                if word_rule and skeys.startswith(word_rule.skeys):
                    matches.append(word_rule)
        return matches

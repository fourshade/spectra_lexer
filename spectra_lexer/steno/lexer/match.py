""" Contains all usable rule matchers for the lexer. """

from typing import Iterable, List, Sequence, Tuple, TypeVar

# Generic marker for the rule reference data type (may be anything).
_RULE_TP = TypeVar("_RULE_TP")
# Marker for the match data type: (rule, unmatched keys, rule start, rule length).
MATCH_TP = Tuple[_RULE_TP, str, int, int]


class IRuleMatcher:
    """ Interface for a class that matches steno rules using a rule's s-keys and/or letters. """

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> Iterable[MATCH_TP]:
        raise NotImplementedError


class _PrefixTree:
    """ A trie-based structure with sequence-based keys that has the distinct advantage of
        quickly returning all values that match a given key or any of its prefixes, in order.
        It also allows duplicate keys, returning a list of all values that match it. """

    _T = TypeVar("_T")

    def __init__(self) -> None:
        """ The root node matches the empty sequence, which is a prefix of everything. """
        self._root = {"values": []}

    def add(self, k:Sequence, v:_T) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until we reach it. """
        node = self._root
        for element in k:
            if element not in node:
                node[element] = {"values": []}
            node = node[element]
        node["values"].append(v)

    def match(self, k:Sequence) -> List[_T]:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from longest prefix matched to shortest. """
        node = self._root
        values = node["values"][:]
        for element in k:
            if element not in node:
                break
            node = node[element]
            values = node["values"] + values
        return values


class PrefixMatcher(IRuleMatcher):
    """ Matches rules that start with certain keys in order, and others in any order (but only within one stroke).
        The performance is heavily dependent on the number of possible unordered keys.
        This is only really required for the asterisk; adding more tends to slow it down more than is worth it. """

    def __init__(self, key_sep:str, unordered_keys:Iterable[str]) -> None:
        filter_unordered = frozenset(unordered_keys).intersection
        self._key_sep = key_sep                    # Steno stroke delimiter.
        self._filter_unordered = filter_unordered  # Filter for unordered keys.
        self._tree = _PrefixTree()                 # Prefix tree for all rules.
        self._ordered_tree = _PrefixTree()         # Prefix tree for rules with only ordered keys.

    def add(self, rule:_RULE_TP, skeys:str, letters:str) -> None:
        """ Index a rule, its skeys string, its letters, and its unordered keys under only the ordered keys.
            The ordered keys may be derived by removing the unordered keys from the full string one-at-a-time. """
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        letters = letters.lower()
        # Unordered keys must be filtered from the first stroke in each string of keys.
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_set = self._filter_unordered(skeys_fs)
        if not unordered_set:
            # Add rules with only ordered keys to a separate tree for faster matching.
            self._ordered_tree.add(skeys, (rule, len(skeys), letters))
        ordered_keys = skeys
        for c in unordered_set:
            ordered_keys = ordered_keys.replace(c, "", 1)
        self._tree.add(ordered_keys, (rule, skeys, letters, unordered_set))

    def match(self, skeys:str, letters:str, *_) -> List[MATCH_TP]:
        """ Make a list of all rules that match a prefix of the ordered keys in <skeys>, a subset of <letters>,
            and a subset of <unordered_set> from the first stroke. This may yield a large number of rules.
            Also return the new key string that would result from removing the keys involved. """
        letters = letters.lower()
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        unordered_set = self._filter_unordered(skeys_fs)
        if not unordered_set:
            return self._match_ordered(skeys, letters)
        matches = []
        ordered_keys = skeys
        for c in unordered_set:
            ordered_keys = ordered_keys.replace(c, "", 1)
        for rule, rsk, rl, ru in self._tree.match(ordered_keys):
            if rl in letters and ru <= unordered_set:
                # Remove matched keys starting from the left and save the remainder.
                # With no guaranteed order, each key must be removed individually.
                skeys_left = skeys
                for c in rsk:
                    skeys_left = skeys_left.replace(c, "", 1)
                matches.append((rule, skeys_left, letters.find(rl), len(rl)))
        return matches

    def _match_ordered(self, skeys:str, letters:str) -> List[MATCH_TP]:
        """ Faster match method for key strings with only ordered keys in the first stroke.
            They cannot match anything with unordered keys, and prefixes may be removed by slicing. """
        matches = []
        for rule, rsklen, rl in self._ordered_tree.match(skeys):
            if rl in letters:
                matches.append((rule, skeys[rsklen:], letters.find(rl), len(rl)))
        return matches


class SpecialMatcher(IRuleMatcher):
    """ Handles special steno rules individually in code. """

    # Names for special steno rules. These are prefixed with their associated keys when defined in JSON.
    # Example: the rule name "*:AB" will match an asterisk that maps to an abbreviation.
    # None of these rules may use up any letters.
    ABBREVIATION = "AB"
    PROPER = "PR"
    AFFIX = "PS"
    UNKNOWN = "??"

    def __init__(self, key_sep:str, unordered_keys:Iterable[str]) -> None:
        all_unordered = set(unordered_keys).issuperset
        self._key_sep = key_sep              # Steno stroke delimiter.
        self._all_unordered = all_unordered  # Filter for strokes with only unordered keys left.
        self._name_dict = {}                 # Contains special rules indexed by reference name.

    def add(self, rule:_RULE_TP, name:str) -> None:
        """ Add a special rule to be matched. Its letters are ignored. """
        self._name_dict[name] = rule

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[MATCH_TP]:
        """ If we only have an asterisk left at the end of a stroke, try to guess its meaning.
            <skeys>           - contains all keys that have not yet been matched.
            <skeys_fs>        - contents of the current leading stroke; should just be the asterisk/special key.
            <word>            - contains all letters in the translation.
            <is_first_stroke> - are we currently parsing the first stroke of the translation? """
        # If there are only unordered keys, look for a special meaning.
        strokes = skeys.split(self._key_sep)
        skeys_fs = strokes[0]
        if not self._all_unordered(skeys_fs):
            return []
        is_first_stroke = (len(strokes) - 1 == all_skeys.count(self._key_sep))
        is_last_stroke = (skeys_fs == skeys)
        # If the word contains a period, it's probably an abbreviation.
        if "." in all_letters:
            rule_type = self.ABBREVIATION
        # If the word has uppercase letters in it, it's probably a proper noun.
        elif all_letters != all_letters.lower():
            rule_type = self.PROPER
        # If we are on either the first or last stroke (and there is more than one), it's probably a prefix or suffix.
        elif is_first_stroke ^ is_last_stroke:
            rule_type = self.AFFIX
        # If execution reaches the end without a valid guess, use the "ambiguous" rule name.
        else:
            rule_type = self.UNKNOWN
        # Look up the rule by name and return it (it *should* exist if the rule files are intact, but also allow None).
        rule_name = skeys_fs + ":" + rule_type
        if rule_name not in self._name_dict:
            return []
        rule = self._name_dict[rule_name]
        return [(rule, skeys[len(skeys_fs):], 0, 0)]


class StrokeMatcher(IRuleMatcher):
    """ For stroke matches, a rule must match the next full stroke and a subset of the current letters. """

    def __init__(self, key_sep:str) -> None:
        self._key_sep = key_sep  # Steno stroke delimiter.
        self._stroke_dict = {}   # Contains rules that match a full stroke only.

    def add(self, rule:_RULE_TP, skeys:str, letters:str) -> None:
        self._stroke_dict[skeys] = letters, rule

    def match(self, skeys:str, letters:str, all_skeys:str, *_) -> List[MATCH_TP]:
        """ We have a complete stroke next if we just started or a stroke separator was just matched. """
        if skeys == all_skeys or all_skeys[-len(skeys)-1] == self._key_sep:
            skeys_fs = skeys.split(self._key_sep, 1)[0]
            if skeys_fs in self._stroke_dict:
                letters = letters.lower()
                stroke_letters, stroke_rule = self._stroke_dict[skeys_fs]
                if stroke_letters in letters:
                    return [(stroke_rule, skeys[len(skeys_fs):], letters.find(stroke_letters), len(stroke_letters))]
        return []


class WordMatcher(IRuleMatcher):
    """ For word matches, a rule must match a prefix of the current keys and the next whitespace-separated word. """

    def __init__(self) -> None:
        self._word_dict = {}  # Contains rules that match a full word only.

    def add(self, rule:_RULE_TP, skeys:str, letters:str) -> None:
        self._word_dict[letters] = skeys, rule

    def match(self, skeys:str, letters:str, all_skeys:str, *_) -> List[MATCH_TP]:
        """ We have a complete word next if we just started or the word pointer is sitting on a space. """
        if skeys == all_skeys or letters[:1] == ' ':
            letters = letters.lower()
            words = letters.split()
            if words:
                first_word = words[0]
                if first_word in self._word_dict:
                    word_skeys, word_rule = self._word_dict[first_word]
                    if skeys.startswith(word_skeys):
                        return [(word_rule, skeys[len(word_skeys):], letters.find(first_word), len(first_word))]
        return []

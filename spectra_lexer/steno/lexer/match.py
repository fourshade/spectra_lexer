from typing import List, Sequence, Tuple, TypeVar

# Generic marker for the rule data type.
_RULE = TypeVar("_RULE")
# Marker for the match data type: (rule, unmatched keys, rule letters).
MATCH_TP = Tuple[_RULE, str, str]


class PrefixTree:
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


class PrefixMatcher:
    """ Matches rules that start with certain keys in order, and others in any order (but only within one stroke).
        The performance is heavily dependent on the number of possible unordered keys.
        This is only really required for the asterisk; adding more tends to slow it down more than is worth it. """

    def __init__(self) -> None:
        self._tree = PrefixTree()          # Prefix tree for all rules.
        self._ordered_tree = PrefixTree()  # Prefix tree for rules with only ordered keys.

    def add(self, rule:_RULE, skeys:str, letters:str, unordered_set=frozenset()) -> None:
        """ Index a rule, its skeys string, its letters, and its unordered keys under only the ordered keys.
            The ordered keys may be derived by removing the unordered keys from the full string one-at-a-time. """
        ordered_keys = skeys
        for c in unordered_set:
            ordered_keys = ordered_keys.replace(c, "", 1)
        if not unordered_set:
            # Add rules with only ordered keys to a separate tree for faster matching.
            self._ordered_tree.add(ordered_keys, (rule, len(skeys), letters))
        self._tree.add(ordered_keys, (rule, skeys, letters, unordered_set))

    def match(self, skeys:str, letters:str, unordered_set=frozenset()) -> List[MATCH_TP]:
        """ Make a list of all rules that match a prefix of the ordered keys in <skeys>, a subset of <letters>,
            and a subset of <unordered_set> from the first stroke. This may yield a large number of rules.
            Also return the new key string that would result from removing the keys involved. """
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
                matches.append((rule, skeys_left, rl))
        return matches

    def _match_ordered(self, skeys:str, letters:str) -> List[MATCH_TP]:
        """ Faster match method for key strings with only ordered keys in the first stroke.
            They cannot match anything with unordered keys, and prefixes may be removed by slicing. """
        matches = []
        for rule, rsklen, rl in self._ordered_tree.match(skeys):
            if rl in letters:
                matches.append((rule, skeys[rsklen:], rl))
        return matches


class SpecialMatcher:
    """ Handles special steno rules individually in code. """

    # Names for special steno rules. These are prefixed with their associated keys when defined in JSON.
    # Example: the rule name "*:AB" will match an asterisk that maps to an abbreviation.
    # None of these rules may use up any letters.
    ABBREVIATION = "AB"
    PROPER = "PR"
    AFFIX = "PS"
    UNKNOWN = "??"

    def __init__(self) -> None:
        self._name_dict = {}  # Contains special rules indexed by reference name.

    def add(self, rule:_RULE, name:str) -> None:
        """ Add a special rule to be matched. Its letters are ignored. """
        self._name_dict[name] = rule

    def match(self, skeys:str, skeys_fs:str, sep_count:int, word:str) -> List[MATCH_TP]:
        """ If we only have an asterisk left at the end of a stroke, try to guess its meaning.
            <skeys>     - contains all keys that have not yet been matched.
            <skeys_fs>  - the asterisk/special key.
            <sep_count> - number of currently recorded separators.
            <word>      - contains all letters in the translation. """
        is_first_stroke = not sep_count
        is_last_stroke = (skeys_fs == skeys)
        # If the word contains a period, it's probably an abbreviation.
        if "." in word:
            rule_type = self.ABBREVIATION
        # If the word has uppercase letters in it, it's probably a proper noun.
        elif word != word.lower():
            rule_type = self.PROPER
        # If we are on either the first or last stroke (and there is more than one), it's probably a prefix or suffix.
        elif is_first_stroke ^ is_last_stroke:
            rule_type = self.AFFIX
        # If execution reaches the end without a valid guess, use the "ambiguous" rule name.
        else:
            rule_type = self.UNKNOWN
        # Look up the rule by name and return it (it *should* exist if the rule files are intact, but also allow None).
        rule_name = skeys_fs + ":" + rule_type
        if rule_name in self._name_dict:
            rule = self._name_dict[rule_name]
            return [(rule, skeys[len(skeys_fs):], "")]
        return []


class StrokeMatcher:

    def __init__(self) -> None:
        self._stroke_dict = {}  # Contains rules that match a full stroke only.

    def add(self, rule:_RULE, skeys:str, letters:str) -> None:
        self._stroke_dict[skeys] = letters, rule

    def match(self, skeys:str, letters:str, skeys_fs:str) -> List[MATCH_TP]:
        # For the stroke dictionary, the rule must match the next full stroke and a subset of <letters>.
        if skeys_fs in self._stroke_dict:
            stroke_letters, stroke_rule = self._stroke_dict[skeys_fs]
            if stroke_letters in letters:
                return [(stroke_rule, skeys[len(skeys_fs):], stroke_letters)]
        return []


class WordMatcher:

    def __init__(self) -> None:
        self._word_dict = {}  # Contains rules that match a full word only.

    def add(self, rule:_RULE, skeys:str, letters:str) -> None:
        self._word_dict[letters] = skeys, rule

    def match(self, skeys:str, letters:str) -> List[MATCH_TP]:
        # For the word dictionary, the rule must match a prefix of <skeys> and the next whitespace-separated word.
        words = letters.split()
        if words:
            first_word = words[0]
            if first_word in self._word_dict:
                word_skeys, word_rule = self._word_dict[first_word]
                if skeys.startswith(word_skeys):
                    return [(word_rule, skeys[len(word_skeys):], first_word)]
        return []

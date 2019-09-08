""" Contains building blocks for the primary steno analysis component - the lexer.
    Much of the code is inlined for performance reasons. """

from functools import reduce
from operator import attrgetter
from typing import Dict, Iterable, List, Sequence, Tuple, TypeVar, Union

from .keys import KeyLayout
from .rules import RuleMapItem, StenoRule


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


_RULE = TypeVar("_RULE")


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

    def match(self, skeys:str, letters:str, unordered_set=frozenset()) -> List[Tuple[_RULE, str]]:
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
                matches.append((rule, skeys_left))
        return matches

    def _match_ordered(self, skeys:str, letters:str) -> List[Tuple[_RULE, str]]:
        """ Faster match method for key strings with only ordered keys in the first stroke.
            They cannot match anything with unordered keys, and prefixes may be removed by slicing. """
        matches = []
        for rule, rsklen, rl in self._ordered_tree.match(skeys):
            if rl in letters:
                matches.append((rule, skeys[rsklen:]))
        return matches


class SpecialMatcher:
    """ Handles special steno rules individually in code. """

    # Names for special steno rules. These are prefixed with their associated keys when defined in JSON.
    # Example: the rule name "*:AB" will match an asterisk that maps to an abbreviation.
    ABBREVIATION = "AB"
    PROPER = "PR"
    AFFIX = "PS"
    UNKNOWN = "??"

    def __init__(self, name_dict:Dict[str, _RULE],
                 stroke_dict:Dict[str, Tuple[str, _RULE]], word_dict:Dict[str, Tuple[str, _RULE]]) -> None:
        self._name_dict = name_dict      # Contains special rules indexed by reference name.
        self._stroke_dict = stroke_dict  # Contains rules that match a full stroke only.
        self._word_dict = word_dict      # Contains rules that match a full word only.

    def match_stroke(self, skeys:str, letters:str, skeys_fs:str) -> List[Tuple[_RULE, str]]:
        # For the stroke dictionary, the rule must match the next full stroke and a subset of <letters>.
        if skeys_fs in self._stroke_dict:
            stroke_letters, stroke_rule = self._stroke_dict[skeys_fs]
            if stroke_letters in letters:
                return [(stroke_rule, skeys[len(skeys_fs):])]
        return []

    def match_word(self, skeys:str, letters:str) -> List[Tuple[_RULE, str]]:
        # For the word dictionary, the rule must match a prefix of <skeys> and the next whitespace-separated word.
        words = letters.split()
        if words and words[0] in self._word_dict:
            word_skeys, word_rule = self._word_dict[words[0]]
            if skeys.startswith(word_skeys):
                return [(word_rule, skeys[len(word_skeys):])]
        return []

    def match_name(self, skeys:str, skeys_fs:str, sep_count:int, word:str) -> List[Tuple[_RULE, str]]:
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
            return [(rule, skeys[len(skeys_fs):])]
        return []


class LexerStateQueue:
    """ The lexer state queue. Each item contains the lexer state at some point in time.
        Implemented using a list of lists: [keys not yet matched, rule1, rule1_start, rule1_length, rule2, ...]. """

    def __init__(self, *, match_all_keys=False) -> None:
        self._states = []
        self._match_all_keys = match_all_keys  # If True, only keep results that match every key in the stroke.
        self.put = self._states.append

    def __iter__(self):
        """ Iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
            from the list; for practical purposes, the iterator index can be considered the start of the queue.
            This index starts at 0 and advances every iteration. Appending items in-place does not affect it. """
        return iter(self._states)

    def best(self) -> List[Union[StenoRule, str, int]]:
        """ Rank the recorded states and return the best one. Going in reverse is faster. """
        assert self._states
        best = reduce(self._keep_better, reversed(self._states))
        if best[0] and self._match_all_keys:
            return self._states[0]
        return best

    def _keep_better(self, current, other, _is_rare=attrgetter("is_rare")) -> List[Union[StenoRule, str, int]]:
        """ Foldable function that keeps one of two lexer states based on which has a greater "value".
            Each criterion is lazily evaluated, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values.
            As it is called repeatedly by reduce(), the full compare sequence
            is inlined to avoid method call overhead. """
        if (-len(current[0]) + len(other[0]) or                                      # Fewest keys unmatched
            sum(current[3::3]) - sum(other[3::3]) or                                 # Most letters matched
            -sum(map(_is_rare, current[1::3])) + sum(map(_is_rare, other[1::3])) or  # Fewest rare child rules
            -len(current) + len(other)) >= 0:                                        # Fewest child rules
            return current
        return other


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    def __init__(self, layout:KeyLayout, rule_sep:_RULE,
                 prefix_matcher:PrefixMatcher, special_matcher:SpecialMatcher) -> None:
        """ Build a lexer object from a key layout and rule matcher. """
        self._layout = layout                    # Has conversion functions between user RTFCRE steno strings to s-keys.
        self._rule_sep = rule_sep                # Separator rule constant; is specifically matched on its own.
        self._prefix_matcher = prefix_matcher    # Contains rules that match by starting with certain keys.
        self._special_matcher = special_matcher  # Matches special rules by reference name.

    def query(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return the best rule that maps the given key string to the given word. """
        results = self._process(keys, word, **kwargs)
        unmatched_keys, *item = results.best()
        if unmatched_keys:
            # Convert unmatched keys back to RTFCRE format first.
            unmatched_keys = self._layout.to_rtfcre(unmatched_keys)
        it = iter(item)
        rulemap = (*map(RuleMapItem, it, it, it),)
        return StenoRule.generated(keys, word, rulemap, unmatched_keys)

    def best_strokes(self, keys_iter:Iterable[str], word:str, **kwargs) -> str:
        """ Return the best (most accurate) set of strokes from <keys_iter> that matches <word>.
            If nothing matches at all, just return the shortest set of strokes. """
        keys_list = sorted(keys_iter, key=len)
        items = [self._process(keys, word, **kwargs).best() for keys in keys_list]
        q = LexerStateQueue()
        for i in items:
            q.put(i)
        best = q.best()
        try:
            return keys_list[items.index(best)]
        except ValueError:
            return keys_list[0]

    def _process(self, keys:str, word:str, **kwargs) -> LexerStateQueue:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of complete rule maps that could possibly produce the translation.
            Use heavy optimization when possible; add only results that aren't optimized away. """
        # Thoroughly parse the key string into s-keys format and return a list of possible maps.
        all_skeys = self._layout.from_rtfcre(keys)
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        lword = word.lower()
        lword_find = lword.find
        # The queue starting state has all keys unmatched and no rules.
        q = LexerStateQueue(**kwargs)
        q_put = q.put
        q_put([all_skeys])
        for skeys, *rmap in q:
            if skeys:
                # Get the rules that would work as the next match in order from fewest keys matched to most.
                wordptr = rmap[-2] + rmap[-1] if rmap else 0
                letters = lword[wordptr:]
                matches = self._match_rules(skeys, letters, rmap[::3], word)
                for rule, unmatched_keys in matches:
                    # Find the new location in the word and the number of letters the rule covers.
                    # Add a queue item with the new map, the remaining keys, and the new position in the word.
                    rule_letters = rule.letters
                    next_wordptr = lword_find(rule_letters, wordptr)
                    q_put([unmatched_keys, *rmap, rule, next_wordptr, len(rule_letters)])
        return q

    def _match_rules(self, skeys:str, letters:str, rules:List[_RULE], all_letters:str) -> List[Tuple[_RULE, str]]:
        """ Search every dictionary for the given keys and letters and return a list of matches. """
        # If our current stroke is empty, a stroke separator is next. There are no better matches; return immediately.
        skeys_fs = self._layout.first_stroke(skeys)
        if not skeys_fs:
            return [(self._rule_sep, skeys[1:])]
        # Start with a list of all rules that match a prefix of <skeys> and a subset of <letters>.
        unordered_set = self._layout.filter_unordered(skeys_fs)
        matches = self._prefix_matcher.match(skeys, letters, unordered_set)
        # We have a complete stroke next if we just started or a stroke separator was just matched.
        is_start = not rules
        if is_start or rules[-1] is self._rule_sep:
            matches += self._special_matcher.match_stroke(skeys, letters, skeys_fs)
        # We have a complete word next if we just started or the word pointer is sitting on a space.
        if is_start or letters[:1] == ' ':
            matches += self._special_matcher.match_word(skeys, letters)
        # If we only have unordered keys left at the end of a stroke, look for a special meaning.
        if unordered_set and unordered_set.issuperset(skeys_fs):
            sep_count = rules.count(self._rule_sep)
            matches += self._special_matcher.match_name(skeys, skeys_fs, sep_count, all_letters)
        return matches

    @classmethod
    def build(cls, layout:KeyLayout, rules:List[StenoRule], rule_sep:StenoRule):
        """ Parse keys from all rules into the case-unique s-keys format and create the lexer with rule matchers. """
        name_dict = {}
        stroke_dict = {}
        word_dict = {}
        prefix_matcher = PrefixMatcher()
        for rule in rules:
            skeys = layout.from_rtfcre(rule.keys)
            letters = rule.letters
            # Internal rules are only used in special cases, by name.
            if rule.is_special:
                name_dict[rule.name] = rule
            # Filter stroke and word rules into their own dicts.
            elif rule.is_stroke:
                stroke_dict[skeys] = letters, rule
            elif rule.is_word:
                word_dict[letters] = skeys, rule
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                # Unordered keys must be filtered from the first stroke in each string of keys.
                skeys_fs = layout.first_stroke(skeys)
                unordered_set = layout.filter_unordered(skeys_fs)
                prefix_matcher.add(rule, skeys, letters, unordered_set)
        special_matcher = SpecialMatcher(name_dict, stroke_dict, word_dict)
        return cls(layout, rule_sep, prefix_matcher, special_matcher)

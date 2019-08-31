""" Contains building blocks for the primary steno analysis component - the lexer.
    Much of the code is inlined for performance reasons. """

from collections import namedtuple
from functools import reduce
from operator import attrgetter
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

from .keys import KeyLayout
from .rules import RuleMapItem, StenoRule


class LexerMatch(namedtuple("LexerMatch", "rule skeys letters skeys_len letters_len")):
    """ Container for a steno rule match with s-keys. Has precalculated lengths for speed.
        rule: StenoRule  - Original immutable rule.
        skeys: str       - Lexer-formatted steno keys that make up the rule.
        letters: str     - Raw English text of the word.
        skeys_len: int   - Length of <skeys>.
        letters_len: int - Length of <letters>. """

    @classmethod
    def special(cls, skeys:str, desc:str):
        """ Create a special (no-letter) rule and place it in a match object. """
        return cls(StenoRule.special(skeys, desc), skeys, "", len(skeys), 0)


class SpecialRuleFinder:
    """ Dictionary for "special" rules, including built-in rules not loaded from JSON. """

    # Identifiers for special rules that are handled individually in code.
    CONFLICT = "CF"
    PROPER = "PR"
    ABBREVIATION = "AB"
    AFFIX = "PS"
    FINGERSPELL = "FS"
    OBSCENE = "OB"

    def __init__(self, sep:str, star:str) -> None:
        self._d = {}           # Contains rules that match by reference name.
        self._key_sep = sep    # Steno key used as stroke separator in both stroke formats.
        self._key_star = star  # Steno key used for special translation-wide matches.
        # A separator rule constant is specifically matched on its own.
        self._rule_sep = LexerMatch.special(sep, "Stroke separator")
        # An unknown special rule constant is required in case no special rules match (or a matched rule is missing).
        self._rule_unknown = LexerMatch.special(star, "purpose unknown\nPossibly resolves a conflict")
        self.update = self._d.update

    def match(self, skeys_fs:str, skeys:str, all_skeys:str, all_letters:str) -> Optional[LexerMatch]:
        """ Check the first stroke for special rules. Return the first one if there are any. """
        # If our current stroke is empty, a stroke separator is next. Return its rule.
        if not skeys_fs:
            return self._rule_sep
        # If we only have a star left at the end of a stroke, try to guess its meaning.
        # If execution reaches the end without a valid guess, return the "ambiguous" rule.
        if skeys_fs == self._key_star:
            rule_type = self._analyze_star(skeys, all_skeys, all_letters)
            return self._d.get(f"{self._key_star}:{rule_type}") or self._rule_unknown

    def _analyze_star(self, skeys:str, all_skeys:str, all_letters:str) -> Optional[str]:
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

    def __init__(self) -> None:
        """ The root node matches the empty sequence, which is a prefix of everything. """
        self._root = {"values": []}  # Source root node of the tree.
        self._compiled = {}          # Last compiled state of the tree.

    def __setitem__(self, k:Sequence, v:object) -> None:
        """ Add a new value to the list under the given key. If it doesn't exist, create nodes until you reach it. """
        node = self._root
        for element in k:
            node = node.get(element) or node.setdefault(element, {"values": []})
        node["values"].append(v)

    def compile(self) -> None:
        """ Finalize the tree by populating a new set of nodes with values from all possible prefixes.
            Must be called to reflect modifications from the root node to the one used by __getitem__. """
        self._compiled = self._compile(self._root, [])

    def _compile(self, src:dict, values:list) -> dict:
        """ Add the <src> node's values to the previous <values> to get all prefixes up to this point.
            Set these on a new compiled node and compile all children by propagating the values recursively. """
        v = src["values"] + values
        dest = {k: self._compile(src[k], v) for k in src if k != "values"}
        dest["values"] = v
        return dest

    def __getitem__(self, k:Sequence) -> list:
        """ From a given sequence, return a list of all of the values that match
            any prefix of it in order from longest prefix matched to shortest. """
        node = self._compiled
        for element in k:
            if element not in node:
                break
            node = node[element]
        return node["values"]


class PrefixRuleFinder:
    """ Search engine that finds rules matching a prefix of steno-ordered keys.
        Steno order may be ignored for certain keys, but this has a large performance and accuracy cost.
        Only the asterisk is used in such a way that this treatment is worth it. """

    def __init__(self, sep:str, star:str) -> None:
        self._tree = PrefixTree()  # Primary search tree.
        self._key_sep = sep        # Steno key used as stroke separator.
        self._key_star = star      # Currently only one unordered key is allowed: the asterisk.

    def update(self, items:Sequence[LexerMatch]) -> None:
        """ Separate the given sets of keys into ordered keys (which contain any prefix) and unordered keys.
            Index the rules, letters, and unordered keys under the ordered keys and (re-)compile the tree. """
        tree = self._tree
        for r in items:
            ordered, unordered = self._unordered_filter(r.skeys)
            tree[ordered] = (r, r.letters, unordered)
        tree.compile()

    def match(self, skeys:str, letters:str) -> List[LexerMatch]:
        """ Return a list of all rules that match a prefix of the ordered keys in <skeys>,
            a subset of <letters>, and a subset of the unordered keys in <skeys>. """
        ordered, unordered = self._unordered_filter(skeys)
        return [r for (r, rl, ru) in self._tree[ordered] if rl in letters and ru <= unordered]

    def _unordered_filter(self, skeys:str, _empty=frozenset()) -> tuple:
        """ Filter out asterisks in the first stroke that may be consumed at any time and return them.
            Also return the remaining ordered keys that must be consumed starting from the left. """
        star = self._key_star
        if (star not in skeys) or (star not in skeys.split(self._key_sep, 1)[0]):
            return skeys, _empty
        return skeys.replace(star, ""), {star}


class LexerResult(tuple):
    """ Simple low-overhead type for a single lexer result. """

    def keep_better(self, other):
        """ Foldable function that keeps one of two lexer results based on which has a greater "value".
            Each criterion is lazily evaluated, with the first non-zero result determining the winner.
            Some criteria are negative, meaning that more accurate maps have smaller values.
            As it is called repeatedly by reduce(), the full compare sequence
            is inlined to avoid method call overhead. """
        rulemap, unmatched, keys, letters = self
        n_rulemap, n_unmatched, n_keys, n_letters = other
        return self if (-len(unmatched)           + len(n_unmatched) or              # Fewest keys unmatched
                        self.letters_matched()    - other.letters_matched() or       # Most letters matched
                        -self.rare_count()        + other.rare_count() or            # Fewest rare rules
                        -len(keys)                + len(n_keys) or                   # Fewest total keys
                        -len(rulemap)             + len(n_rulemap)) >= 0 else other  # Fewest child rules

    def letters_matched(self, _get_letters=attrgetter("rule.letters")) -> int:
        """ Get the number of characters matched by mapped rules. """
        return sum(map(len, map(_get_letters, self[0])))

    def rare_count(self, _get_rare=attrgetter("rule.flags.rare")) -> int:
        """ Get the number of rare rules in the map. """
        return sum(map(_get_rare, self[0]))


class StenoLexer:
    """ The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
        patterns it can find, then sorts among them to find what it considers the most likely to be correct. """

    def __init__(self, layout:KeyLayout, special_finder:SpecialRuleFinder, prefix_finder:PrefixRuleFinder) -> None:
        """ Build a lexer object from a key layout and finders. The rules must be added later. """
        self._stroke_dict = {}                      # Contains rules that match a full stroke only.
        self._word_dict = {}                        # Contains rules that match a full word only (whitespace-separated).
        self._special_finder = special_finder       # Finds rules that match by reference name.
        self._prefix_finder = prefix_finder         # Finds rules that match by starting with certain keys in order.
        self._key_sep = layout.SEP                  # Steno key used as stroke separator in both stroke formats.
        self._cleanse = layout.cleanse_from_rtfcre  # Performs thorough conversions on RTFCRE steno strings.
        self._to_rtfcre = layout.to_rtfcre          # Conversion function back from s-keys to RTFCRE.

    def update(self, rules:Dict[str, StenoRule]) -> None:
        """ Update the lexer by sorting the given rules into specific dictionaries or rule finders based on flags. """
        special_entries = {}
        prefix_entries = []
        for n, r in rules.items():
            # All rules must have their keys parsed into the case-unique s-keys format.
            skeys = self._cleanse(r.keys)
            letters = r.letters
            flags = r.flags
            lr = LexerMatch(r, skeys, letters, len(skeys), len(letters))
            # Internal rules are only used in special cases, by name.
            if flags.special:
                special_entries[n] = lr
            # Filter stroke and word rules into their own dicts.
            elif flags.stroke:
                self._stroke_dict[skeys] = lr
            elif flags.word:
                self._word_dict[letters] = lr
            # Everything else gets added to the tree-based prefix dictionary.
            else:
                prefix_entries.append(lr)
        self._special_finder.update(special_entries)
        self._prefix_finder.update(prefix_entries)

    def query(self, keys:str, word:str, **kwargs) -> StenoRule:
        """ Return the best rule that maps the given key string to the given word. """
        results = [*self._process(keys, word, **kwargs)]
        return self._generate(results, keys, word)

    def best_strokes(self, items:Iterable[Tuple[str, str]], **kwargs) -> str:
        """ Return the best (most accurate) set of strokes out of all given (keys, word) pairs.
            If nothing matches at all, just return the first set of strokes. """
        first, *others = pairs = [*items]
        results = [r for keys, word in pairs for r in self._process(keys, word, **kwargs)]
        return self._generate(results, *first).keys

    def _process(self, keys:str, word:str, match_all_keys:bool=False) -> Iterator[LexerResult]:
        """ Given a string of formatted s-keys and a matching translation, use steno rules to match keys to printed
            characters in order to generate a series of complete rule maps that could possibly produce the translation.
            If <match_all_keys> is True, only yield results that match every key in the stroke.
            Use heavy optimization when possible; yield only results that aren't optimized away. """
        # Thoroughly cleanse and parse the key string into s-keys format first (user strokes cannot be trusted).
        all_skeys = self._cleanse(keys)
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        lword = word.lower()
        # The queue is a list of tuples, each containing the state of the lexer at some point in time.
        # Each tuple includes the keys not yet matched, the current position in the word, and the current rule map.
        # Initialize the queue with the start position ready and start processing.
        queue = [(all_skeys, 0, [])]
        queue_add = queue.append
        # Simple iteration over a list is much faster than popping from a deque. Nothing *actually* gets removed
        # from the list; for practical purposes, the iterator pointer can be considered the start of the queue.
        for skeys, wordptr, rulemap in queue:
            letters_left = lword[wordptr:]
            # Get the rules that would work as the next match in order from fewest keys matched to most.
            for r, r_skeys, r_letters, r_skeys_len, r_letters_len in self._match(skeys, letters_left, all_skeys, word):
                # Make a copy of the current map and add the new rule + its location in the word.
                new_wordptr = wordptr + letters_left.find(r_letters)
                new_map = rulemap + [RuleMapItem(r, new_wordptr, r_letters_len)]
                # Remove all matched keys and keep the remainder.
                if skeys[:r_skeys_len] == r_skeys:
                    # Fast path: if the keys are a direct prefix, just cut it off.
                    skeys_left = skeys[r_skeys_len:]
                else:
                    # Otherwise, each key must be removed individually.
                    skeys_left = skeys
                    for c in r_skeys:
                        skeys_left = skeys_left.replace(c, "", 1)
                # A "complete" map is one that matches every one of the keys to a rule.
                # If we need all keys to be matched, don't add incomplete maps.
                if not skeys_left or not match_all_keys:
                    yield LexerResult((new_map, skeys_left, keys, word))
                    if not skeys_left:
                        # If all keys are matched, continue without adding to the queue.
                        continue
                # Add a queue item with the remaining keys, the new position in the word, and the new map.
                queue_add((skeys_left, new_wordptr + r_letters_len, new_map))

    def _match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[LexerMatch]:
        """ Return a list of rules that match the given keys and letters in any of the dictionaries. """
        skeys_fs = skeys.split(self._key_sep, 1)[0]
        # For special single-key end-cases, there are no better matches, so return immediately if one is found.
        special_rule = self._special_finder.match(skeys_fs, skeys, all_skeys, all_letters)
        if special_rule is not None:
            return [special_rule]
        # Try to match keys by prefix. This may yield a large number of rules.
        matches = self._prefix_finder.match(skeys, letters)
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

    def _generate(self, results:List[LexerResult], *defaults:str) -> StenoRule:
        """ Rank results from the lexer and keep the best one, convert unmatched keys back to RTFCRE format,
            and create a new rule with the correct caption and flags. Going in reverse is faster. """
        if not results:
            # If nothing matched at all, make a blank result with the default keys and word.
            keys, letters = defaults
            results = [LexerResult(([], keys, keys, letters))]
        rulemap, unmatched, keys, letters = reduce(LexerResult.keep_better, reversed(results))
        if unmatched:
            return StenoRule.unmatched(keys, letters, rulemap, self._to_rtfcre(unmatched))
        return StenoRule.generated(keys, letters, rulemap)

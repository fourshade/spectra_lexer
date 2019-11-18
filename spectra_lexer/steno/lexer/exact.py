""" Module for by exact string rule matching. """

from typing import List

from .base import IRuleMatcher, MATCH_TP, RULE_ID


class StrokeMatcher(IRuleMatcher):
    """ Matches rules against the next full stroke exactly and a subset of the current letters. """

    def __init__(self, key_sep:str) -> None:
        self._key_sep = key_sep     # Steno stroke delimiter.
        self._rules_by_stroke = {}  # Contains rules that match a full stroke only.

    def add(self, rule_id:RULE_ID, skeys:str, letters:str) -> None:
        self._rules_by_stroke[skeys] = rule_id, letters

    def match(self, skeys:str, letters:str, all_skeys:str, *_) -> List[MATCH_TP]:
        """ We have a complete stroke next if we just started or a stroke separator was just matched. """
        if skeys == all_skeys or all_skeys[-len(skeys)-1] == self._key_sep:
            skeys_fs = skeys.split(self._key_sep, 1)[0]
            if skeys_fs in self._rules_by_stroke:
                letters = letters.lower()
                rule_id, stroke_letters = self._rules_by_stroke[skeys_fs]
                if stroke_letters in letters:
                    return [(rule_id, skeys[len(skeys_fs):], letters.find(stroke_letters), len(stroke_letters))]
        return []


class WordMatcher(IRuleMatcher):
    """ Matches rules against the next (whitespace-separated) word exactly and a prefix of the current keys. """

    def __init__(self) -> None:
        self._rules_by_word = {}  # Contains rules that match a full word only.

    def add(self, rule_id:RULE_ID, skeys:str, letters:str) -> None:
        self._rules_by_word[letters] = rule_id, skeys

    def match(self, skeys:str, letters:str, all_skeys:str, *_) -> List[MATCH_TP]:
        """ We have a complete word next if we just started or the word pointer is sitting on a space. """
        if skeys == all_skeys or letters[:1] == ' ':
            letters = letters.lower()
            words = letters.split()
            if words:
                first_word = words[0]
                if first_word in self._rules_by_word:
                    rule_id, word_skeys = self._rules_by_word[first_word]
                    if skeys.startswith(word_skeys):
                        return [(rule_id, skeys[len(word_skeys):], letters.find(first_word), len(first_word))]
        return []

""" Contains special-case rule matchers for the lexer. """

from typing import Callable, List

from .base import IRuleMatcher, MATCH_TP, RULE_TP


class SpecialMatcher(IRuleMatcher):
    """ Handles special steno rules individually in code. """

    def __init__(self, key_sep:str, key_special:str) -> None:
        self._key_sep = key_sep  # Steno stroke delimiter.
        self._rule_tests = []    # Contains special rules and their test functions.
        # If the special key is at the end of a stroke, these are the possibilities for the next two characters.
        self._valid_next_two_chars = {key_special, key_special + key_sep}

    def add_rule_abbreviation(self, rule:RULE_TP) -> None:
        def test(skeys:str, all_skeys:str, all_letters:str) -> bool:
            """ If the letters contain a period, it's probably an abbreviation. """
            return "." in all_letters
        self._add_test(rule, test)

    def add_rule_proper(self, rule:RULE_TP) -> None:
        def test(skeys:str, all_skeys:str, all_letters:str) -> bool:
            """ If some of the letters are uppercase, it's probably a proper noun. """
            return all_letters != all_letters.lower()
        self._add_test(rule, test)

    def add_rule_affix(self, rule:RULE_TP) -> None:
        def test(skeys:str, all_skeys:str, all_letters:str, _sep=self._key_sep) -> bool:
            """ If we are on either the first or last stroke (and there is more than one),
                it's probably a prefix or suffix. """
            is_first_stroke = (skeys.count(_sep) == all_skeys.count(_sep))
            is_last_stroke = (_sep not in skeys)
            return is_first_stroke ^ is_last_stroke
        self._add_test(rule, test)

    def add_rule_fallback(self, rule:RULE_TP) -> None:
        """ If execution reaches this point without a valid guess, use an "ambiguous" rule as a fallback. """
        self._add_test(rule, lambda *args: True)

    def _add_test(self, rule:RULE_TP, test:Callable[[str, str, str], bool]) -> None:
        self._rule_tests.append((rule, test))

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[MATCH_TP]:
        """ If we only have a special key left at the end of a stroke, try to guess its meaning.
            <skeys>        - contains all keys that have not yet been matched.
            <letters>      - contains all letters that have not yet been matched.
            <skeys_fs>     - contains all keys in the translation.
            <all_letters>  - contains all letters in the translation. """
        if skeys[:2] in self._valid_next_two_chars:
            # Return the first rule whose test returns True (if any).
            for rule, test in self._rule_tests:
                if test(skeys, all_skeys, all_letters):
                    return [(rule, skeys[1:], 0, 0)]
        return []

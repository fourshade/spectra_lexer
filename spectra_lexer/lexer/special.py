""" Module for matching special-case rules. These are usually modifiers involving the asterisk. """

from typing import Callable, List

from .base import IRuleMatcher, MATCH_TP, LexerRule


class SpecialMatcher(IRuleMatcher):
    """ Handles special steno rules individually in code. """

    def __init__(self, key_sep:str) -> None:
        self._key_sep = key_sep             # Steno stroke delimiter.
        self._rule_tests = []               # Contains special rules and their test functions.
        self._valid_next_two_chars = set()  # Possibilities for the next two characters to start matching.

    @staticmethod
    def _test_rule_abbreviation(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If the letters contain a period, it's probably an abbreviation. """
        return "." in all_letters

    def add_rule_abbreviation(self, rule:LexerRule) -> None:
        self._add_test(rule, self._test_rule_abbreviation)

    @staticmethod
    def _test_rule_proper(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If some of the letters are uppercase, it's probably a proper noun. """
        return all_letters != all_letters.lower()

    def add_rule_proper(self, rule:LexerRule) -> None:
        self._add_test(rule, self._test_rule_proper)

    def _test_rule_affix(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If we are on either the first or last stroke (and there is more than one),
            it's probably a prefix or suffix. """
        sep = self._key_sep
        is_first_stroke = (skeys.count(sep) == all_skeys.count(sep))
        is_last_stroke = (sep not in skeys)
        return is_first_stroke ^ is_last_stroke

    def add_rule_affix(self, rule:LexerRule) -> None:
        self._add_test(rule, self._test_rule_affix)

    @staticmethod
    def _test_rule_fallback(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If execution reaches this point without a valid guess, use a guaranteed fallback rule. """
        return True

    def add_rule_fallback(self, rule_id:LexerRule) -> None:
        self._add_test(rule_id, self._test_rule_fallback)

    def _add_test(self, rule:LexerRule, test:Callable[[str, str, str], bool]) -> None:
        """ Add a special rule test. For pickleability, the callable *cannot* be an inner function or lambda. """
        self._rule_tests.append((rule, test))
        self._add_valid_chars(rule)

    def _add_valid_chars(self, rule:LexerRule) -> None:
        """ Special rules must use only one steno key. Any letters are ignored.
            To start special matching, this key plus a stroke separator must be next.
            The key by itself will also match a 2-character slice if it is the only one left. """
        skey = rule.skeys
        assert len(skey) == 1
        self._valid_next_two_chars |= {skey, skey + self._key_sep}

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
                    return [(rule, skeys[1:], 0)]
        return []

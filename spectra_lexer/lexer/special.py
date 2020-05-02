""" Module for matching special-case rules. These are usually modifiers involving the asterisk. """

from typing import Callable, List

from .base import IRuleMatcher, LexerRule, RuleMatch


class SpecialMatcher(IRuleMatcher):
    """ Handles special steno rules individually in code. """

    def __init__(self, key_sep:str) -> None:
        assert len(key_sep) == 1
        self._key_sep = key_sep             # Steno stroke delimiter.
        self._rule_tests = []               # Contains special rules and their test functions.
        self._valid_next_two_chars = set()  # Possibilities for the next two characters to start matching.
        # Associates external IDs with a few hard-coded rule-matching tests.
        self._test_methods = {"~ABBR": self._test_rule_abbreviation,
                              "~PROP": self._test_rule_proper,
                              "~PFSF": self._test_rule_affix,
                              "~????": self._test_rule_fallback}

    @staticmethod
    def _test_rule_abbreviation(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If the letters contain a period, it's probably an abbreviation. """
        return "." in all_letters

    @staticmethod
    def _test_rule_proper(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If some of the letters are uppercase, it's probably a proper noun. """
        return all_letters != all_letters.lower()

    def _test_rule_affix(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If we are on either the first or last stroke (and there is more than one),
            it's probably a prefix or suffix. """
        sep = self._key_sep
        is_first_stroke = (skeys.count(sep) == all_skeys.count(sep))
        is_last_stroke = (sep not in skeys)
        return is_first_stroke ^ is_last_stroke

    @staticmethod
    def _test_rule_fallback(skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If execution reaches this point without a valid guess, use a guaranteed fallback rule. """
        return True

    def _add_valid_chars(self, rule:LexerRule) -> None:
        """ Special rules must use only one steno key. Any letters are ignored.
            To start special matching, this key plus a stroke separator must be next.
            The key by itself will also match a 2-character slice if it is the only one left. """
        skey = rule.skeys
        assert len(skey) == 1
        self._valid_next_two_chars |= {skey, skey + self._key_sep}

    def add_test(self, rule:LexerRule, test:Callable[[str, str, str], bool]) -> None:
        """ Add a special rule test. For pickleability, the callable *cannot* be an inner function or lambda. """
        self._rule_tests.append((rule, test))
        self._add_valid_chars(rule)

    def add_by_id(self, rule:LexerRule, test_id:str) -> bool:
        """ Add a special rule test defined by a string ID. Return False if the ID is not recognized. """
        method = self._test_methods.get(test_id, None)
        if method is None:
            return False
        self.add_test(rule, method)
        return True

    def match(self, skeys:str, letters:str, all_skeys:str, all_letters:str) -> List[RuleMatch]:
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

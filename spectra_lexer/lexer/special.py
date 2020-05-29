""" Module for matching special-case rules. These are usually modifiers involving the asterisk. """

from typing import Callable, List

from .base import IRuleMatcher, LexerRule, RuleMatch


class DelimiterMatcher(IRuleMatcher):
    """ Handles single steno key delimiter rules. """

    def __init__(self) -> None:
        self._delim_rules = {}

    def add(self, rule:LexerRule) -> None:
        """ Add a delimiter rule. It may not have letters. """
        skey = rule.skeys
        if len(skey) != 1:
            raise ValueError("Delimiter rules must have exactly one key.")
        if rule.letters:
            raise ValueError("Delimiter rules may not have letters.")
        self._delim_rules[skey] = rule

    def match(self, skeys:str, *_) -> List[RuleMatch]:
        """ Match a delimiter only if it is at the head of the key string. """
        head = skeys[:1]
        if head in self._delim_rules:
            rule = self._delim_rules[head]
            return [(rule, skeys[1:], 0)]
        return []


class SpecialMatcher(IRuleMatcher):
    """ Handles special steno rules individually in code. """

    class Predicate:
        """ Decorator for a hard-coded predicate method to match a special use case of the asterisk. """
        LIST = []

        def __init__(self, desc:str, repl=""):
            self.desc = desc  # Rule description.
            self.repl = repl  # Replacement for the special key's contents on diagrams.

        def __call__(self, func:Callable) -> Callable:
            self.meth_name = func.__name__
            self.LIST.append(self)
            return func

    def __init__(self, key_sep:str) -> None:
        assert len(key_sep) == 1
        self._key_sep = key_sep             # Steno stroke delimiter.
        self._rule_tests = []               # Contains special rules and their test functions.
        self._valid_next_two_chars = set()  # Possibilities for the next two characters to start matching.

    @Predicate("may indicate an abbreviation", ".")
    def _test_rule_abbreviation(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If the letters contain a period, it's probably an abbreviation. """
        return "." in all_letters

    @Predicate("may indicate a proper noun\n(names, places, etc.)", "↑")
    def _test_rule_proper(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If some of the letters are uppercase, it's probably a proper noun. """
        return all_letters != all_letters.lower()

    @Predicate("may indicate a prefix or suffix stroke", "+")
    def _test_rule_affix(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If we are on either the first or last stroke (and there is more than one),
            it's probably a prefix or suffix. """
        sep = self._key_sep
        is_first_stroke = (skeys.count(sep) == all_skeys.count(sep))
        is_last_stroke = (sep not in skeys)
        return is_first_stroke ^ is_last_stroke

    @Predicate("purpose unknown\nPossibly resolves a conflict", "?")
    def _test_rule_fallback(self, skeys:str, all_skeys:str, all_letters:str) -> bool:
        """ If execution reaches this point without a valid guess, use a guaranteed fallback rule. """
        return True

    def _add_valid_chars(self, skey:str) -> None:
        """ Allow this key to start special matching when found alone or followed by a stroke separator.
            (The key by itself will still match a 2-character slice if it is the only key left.) """
        self._valid_next_two_chars |= {skey, skey + self._key_sep}

    def add_test(self, rule:LexerRule, pred:Predicate) -> None:
        """ Add a special rule test. Special rules must use only one steno key and no letters.
            For pickleability, predicates cannot be nested functions, but bound methods will work. """
        skey = rule.skeys
        if len(skey) != 1:
            raise ValueError("Special rules must have exactly one key.")
        if rule.letters:
            raise ValueError("Special rules may not have letters.")
        self._add_valid_chars(skey)
        test = getattr(self, pred.meth_name)
        self._rule_tests.append((rule, test))

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

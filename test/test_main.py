#!/usr/bin/env python3

""" Unit tests for lexical analysis and graphical rendering. """

from collections import Counter

import pytest

from .base import FACTORY, KEY_LAYOUT, RULES, TEST_TRANSLATIONS

VALID_KEYS = KEY_LAYOUT.valid_rtfcre()
IGNORED_KEYS = KEY_LAYOUT.dividers()


@pytest.mark.parametrize("rule", RULES)
def test_rules(rule) -> None:
    """ Go through each rule and perform integrity checks. """
    key_counter = Counter(rule.keys)
    # Every rule must match at least one key.
    assert key_counter
    # All keys must be valid RTFCRE characters.
    assert key_counter.keys() <= VALID_KEYS
    if rule:
        # Check that the rulemap positions all fall within the legal bounds (i.e. within the parent's letters)
        # Make sure the child rules contain all the keys of the parent between them, and no extras.
        parent_len = len(rule.letters)
        for item in rule:
            assert item.start >= 0
            assert item.length >= 0
            assert item.start + item.length <= parent_len
            keys = item.child.keys
            key_counter.subtract(keys)
        mismatched = [k for k in key_counter if key_counter[k] and k not in IGNORED_KEYS]
        assert not mismatched, f"Entry {rule.id} has mismatched keys vs. its child rules: {mismatched}"


ANALYZER = FACTORY.build_analyzer()
DISPLAY = FACTORY.build_display_engine()


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATIONS.items())
def test_analysis(keys, letters) -> None:
    """ The parsing tests fail if the lexer can't match all the keys. """
    analysis = ANALYZER.query(keys, letters)
    assert analysis
    for item in analysis:
        assert not item.child.is_unmatched, f"Lexer failed to match all keys on {keys} -> {letters}."
    # Rule start positions must be non-negative and increasing monotonic.
    positions = [c.start for c in analysis]
    assert positions == sorted(map(abs, positions))
    # Perform test for analysis output. Currently only checks that the output doesn't raise.
    assert DISPLAY.process(analysis)

#!/usr/bin/env python3

""" Unit tests for lexical analysis and graphical rendering. """

from collections import Counter

import pytest

from .base import FACTORY, KEY_LAYOUT, RULES, RULES_DICT, TEST_TRANSLATIONS
from spectra_lexer.steno.board import BoardElementParser
from spectra_lexer.steno.graph import GraphEngine
from spectra_lexer.steno.lexer import StenoLexerFactory

IGNORED_KEYS = {KEY_LAYOUT.sep, KEY_LAYOUT.split}
VALID_FLAGS = set()
for cls in (BoardElementParser, GraphEngine, StenoLexerFactory):
    for v in vars(cls).values():
        if isinstance(v, str) and v.isupper():
            VALID_FLAGS.add(v)


@pytest.mark.parametrize("rule", RULES)
def test_rules(rule) -> None:
    """ Go through each rule and perform integrity checks. First verify that all flags are valid. """
    flags = rule.flags
    for f in flags:
        assert f in VALID_FLAGS, f"Entry {rule} has illegal flag: {f}"
    rulemap = rule.rulemap
    if rulemap:
        # Check that the rulemap positions all fall within the legal bounds (i.e. within the parent's letters)
        # Make sure the child rules contain all the keys of the parent between them, and no extras.
        parent_len = len(rule.letters)
        key_count = Counter(rule.keys)
        for item in rulemap:
            assert item.start >= 0
            assert item.length >= 0
            assert item.start + item.length <= parent_len
            keys, letters = RULES_DICT[item.name]
            key_count.subtract(keys)
        mismatched = [k for k in key_count if key_count[k] and k not in IGNORED_KEYS]
        assert not mismatched, f"Entry {rule} has mismatched keys vs. its child rules: {mismatched}"


LEXER = FACTORY.build_lexer()
BOARD_ENGINE = FACTORY.build_board_engine()
GRAPH_ENGINE = FACTORY.build_graph_engine()


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATIONS.items())
def test_analysis(keys, letters) -> None:
    """ The parsing tests fail if the lexer can't match all the keys. """
    skeys = KEY_LAYOUT.from_rtfcre(keys)
    result = LEXER.query(skeys, letters)
    unmatched = result.unmatched_skeys()
    assert not unmatched, f"Lexer failed to match all keys on {keys} -> {letters}."
    # Rule names must all refer to rules that exist.
    names = result.rule_names()
    for name in names:
        assert name in RULES_DICT
    # Rule positions must be non-negative and increasing monotonic.
    positions = result.rule_positions()
    assert positions == sorted(map(abs, positions))
    # Rule lengths must be non-negative.
    for length in result.rule_lengths():
        assert length >= 0
    # Perform test for board diagram output. Currently only checks that the output doesn't raise.
    BOARD_ENGINE.from_keys(skeys)
    BOARD_ENGINE.from_rules(names)
    # Perform test for text graph output. Mainly limited to examining the node tree for consistency.
    # The root node uses the top-level rule and has no ancestors.
    root = GRAPH_ENGINE.make_tree(letters, list(result))
    # Every node available for interaction descends from it and is unique.
    nodes_list = [*root]
    nodes_set = set(nodes_list)
    assert len(nodes_list) == len(nodes_set)

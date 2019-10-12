#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

from collections import Counter
import os
import re

import pytest

from spectra_lexer import plover
from spectra_lexer.app import StenoMain
from spectra_lexer.io import ResourceIO
from spectra_lexer.steno.rules import StenoRule
from spectra_lexer.steno.search import ExampleSearchEngine, TranslationsSearchEngine


def _test_file_path(filename:str) -> str:
    """ Get the full file path for program test data by type (e.g. translations that should all pass with matches). """
    return os.path.join(__file__, "..", "data", filename)


# Load resources using default command-line arguments and create components as we need them.
opts = StenoMain()
IO = ResourceIO()
RESOURCES = opts.build_resources()
ENGINE = RESOURCES.build_engine()
KEY_LAYOUT = ENGINE._layout
RULE_PARSER = ENGINE._rule_parser
LEXER = ENGINE._lexer
BOARD_ENGINE = ENGINE._board_engine
GRAPH_ENGINE = ENGINE._graph_engine
RULES_LIST = RULE_PARSER.to_list()
RULES_DICT = {rule.name: rule for rule in RULES_LIST}
IGNORED_KEYS = set("/-")
VALID_FLAGS = {v for v in vars(StenoRule).values() if isinstance(v, str)}


@pytest.mark.parametrize("rule", RULES_LIST)
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
            child_rule = RULES_DICT[item.name]
            assert item.start >= 0
            assert item.length >= 0
            assert item.start + item.length <= parent_len
            key_count.subtract(child_rule.keys)
        mismatched = [k for k in key_count if key_count[k] and k not in IGNORED_KEYS]
        assert not mismatched, f"Entry {rule} has mismatched keys vs. its child rules: {mismatched}"


TRANSLATIONS = IO.json_read(_test_file_path("translations.json"))
TRANSLATIONS_ENGINE = TranslationsSearchEngine(TRANSLATIONS)


@pytest.mark.parametrize("keys, word", TRANSLATIONS.items())
def test_translations_search(keys, word) -> None:
    """ Go through each loaded test translation and check the search method in all modes.
        Search should return a list with only the item itself (or its value) in any mode. """
    assert TRANSLATIONS_ENGINE.search(keys, count=2, strokes=True) == [keys]
    assert TRANSLATIONS_ENGINE.search(word, count=2, strokes=False) == [word]
    assert TRANSLATIONS_ENGINE.search(keys, count=None, strokes=True) == [word]
    assert TRANSLATIONS_ENGINE.search(word, count=None, strokes=False) == [keys]
    assert TRANSLATIONS_ENGINE.search(re.escape(keys), count=2, strokes=True, regex=True) == [keys]
    assert TRANSLATIONS_ENGINE.search(re.escape(word), count=2, strokes=False, regex=True) == [word]


INDEX = IO.json_read(_test_file_path("index.json"))
INDEX_ENGINE = ExampleSearchEngine(INDEX)


@pytest.mark.parametrize("rule_name", INDEX.keys())
def test_index_search(rule_name) -> None:
    """ Any rule with translations in the index should have its keys and letters somewhere in every entry. """
    rule = RULE_PARSER.get(rule_name)
    wresults = INDEX_ENGINE.search(rule_name, "", count=100, strokes=False)
    assert all([rule.letters in r for r in wresults])
    kresults = INDEX_ENGINE.search(rule_name, "", count=100, strokes=True)
    all_keys = set(rule.keys) - IGNORED_KEYS
    assert all_keys == all_keys.intersection(*kresults)


@pytest.mark.parametrize("keys, letters", TRANSLATIONS.items())
def test_analysis(keys, letters) -> None:
    """ The parsing tests fail if the lexer can't match all the keys. """
    skeys = KEY_LAYOUT.from_rtfcre(keys)
    result = LEXER.query(skeys, letters)
    unmatched = result.unmatched_skeys()
    assert not unmatched, f"Lexer failed to match all keys on {keys} -> {letters}."
    # Perform test for board diagram output. Currently only checks that the output doesn't raise.
    names = result.rule_names()
    BOARD_ENGINE.from_keys(skeys)
    BOARD_ENGINE.from_rules(names)
    # Perform test for text graph output. Mainly limited to examining the node tree for consistency.
    positions = result.rule_positions()
    lengths = result.rule_lengths()
    connections = list(zip(names, positions, lengths))
    # The root node uses the top-level rule and has no ancestors.
    root = GRAPH_ENGINE.make_tree(letters, connections)
    # Every node available for interaction descends from it and is unique.
    nodes_list = [*root]
    nodes_set = set(nodes_list)
    assert len(nodes_list) == len(nodes_set)


def test_plover() -> None:
    """ Make sure the Plover plugin can convert dicts between tuple-based keys and string-based keys. """
    plover.test_convert(TRANSLATIONS)

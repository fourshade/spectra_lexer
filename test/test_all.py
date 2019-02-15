#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

import re
from itertools import starmap

import pytest

from spectra_lexer import Component
from spectra_lexer.board import BoardRenderer
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.graph import GraphRenderer
from spectra_lexer.rules import RuleFlags, RulesManager
from spectra_lexer.search import SearchEngine
from spectra_lexer.translations import TranslationsManager
from test import get_test_filename


def direct_connect(cmp:Component, subcmp:Component) -> None:
    """ Connect one component directly to another without an engine for basic calls. """
    cmd_dict = dict(subcmp.engine_commands())
    def direct_call(cmd:str, *args, **kwargs) -> callable:
        c = cmd_dict.get(cmd)
        if c:
            return c[0](*args, **kwargs)
    cmp.engine_connect(direct_call)


# Create components for the tests in order as we need them.
FILE = FileHandler()
RULES = RulesManager()
direct_connect(RULES, FILE)


def test_dict_files():
    """ Load and perform basic integrity tests on the individual built-in rules dictionaries. """
    full_dict = {}
    for d in RULES._load(RULES.files):
        # Check for rules that have identical names (keys)
        conflicts = set(d).intersection(full_dict)
        assert not conflicts, "Dictionary key {} contained in two or more files".format(conflicts)
        full_dict.update(d)


RULES_DICT = RULES.load()


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = r.flags - RuleFlags
        assert not bad_flags, "Entry {} has illegal flag(s): {}".format(r, bad_flags)
    # A rule with children in a rulemap must conform to strict rules for successful parsing.
    # These tests only work for rules that do not allow the same key to appear in two different strokes.
    if r.rulemap:
        child_key_sets = [set(cr.rule.keys) for cr in r.rulemap]
        combined_child_keys = set()
        # Make sure none of the child rules have overlapping keys.
        for s in child_key_sets:
            conflicts = combined_child_keys & s
            assert not conflicts, "Entry {} has child rules with overlapping keys: {}".format(r, conflicts)
            combined_child_keys |= s
        # Make sure the child rules contain all the keys of the parent between them (and no extras).
        key_diff = set(r.keys) ^ combined_child_keys
        assert not key_diff, "Entry {} has mismatched keys vs. its child rules: {}".format(r, key_diff)


TRANSLATIONS = TranslationsManager()
direct_connect(TRANSLATIONS, FILE)
TRANSLATIONS_DICT = TRANSLATIONS.load([get_test_filename()])
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())
LEXER = StenoLexer()
LEXER.set_rules(RULES_DICT)
LEXER.need_all_keys = True
TEST_RESULTS = list(starmap(LEXER.query, TEST_TRANSLATIONS))


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_lexer(result):
    """ The parsing tests fail if the parser can't match all the keys. """
    rulemap = result.rulemap
    assert rulemap, "Lexer failed to match all keys on {} -> {}.".format(result.keys, result.letters)


SEARCH = SearchEngine()
SEARCH.set_translations(TRANSLATIONS_DICT)


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_search(trial):
    """ Go through each loaded test translation and check the search engine in all modes. """
    keys, word = trial
    # Search should return a list containing the item and the item itself in both directions and in either mode.
    SEARCH.reset()
    assert SEARCH.on_input(word) == ([word], word)
    SEARCH.set_mode_strokes(True)
    assert SEARCH.on_input(keys) == ([keys], keys)
    SEARCH.set_mode_regex(True)
    assert SEARCH.on_input(re.escape(keys)) == ([keys], keys)
    SEARCH.set_mode_strokes(False)
    assert SEARCH.on_input(re.escape(word)) == ([word], word)


BOARD = BoardRenderer()
direct_connect(BOARD, FILE)
BOARD_DICT = BOARD.load()
BOARD.set_rules(RULES_DICT)
BOARD.set_elements(BOARD_DICT)


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_board(result):
    """ Perform all tests for board diagram output. Currently only checks that the output isn't empty. """
    elements, desc = BOARD.get_info(result)
    assert elements
    assert desc


GRAPH = GraphRenderer()


@pytest.mark.parametrize("result", TEST_RESULTS)
def test_graph(result):
    """ Perform all tests for text graph output. Mainly limited to examining the node tree for consistency. """
    GRAPH.generate(result)
    # The root node starts in the upper left and has no parent.
    root = GRAPH._graph._locator.select(0, 0)
    assert root.parent is None
    # Every other node descends from it and is unique.
    all_nodes_list = root.get_descendents()
    all_nodes_set = set(all_nodes_list)
    assert len(all_nodes_list) == len(all_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all([node.parent in all_nodes_set for node in all_nodes_list[1:]])
    # The nodes available for interaction must be a subset of this collection.
    assert all_nodes_set >= set(GRAPH._graph._formatter)

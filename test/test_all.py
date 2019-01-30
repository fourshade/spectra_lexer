#!/usr/bin/env python3

""" Main test module for the Spectra steno lexer. Currently handles all major components except the GUI. """

import re

import pytest

from spectra_lexer import Component
from spectra_lexer.dict.rules import RulesManager
from spectra_lexer.dict.translations import TranslationsManager
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.lexer.match import MATCH_FLAGS
from spectra_lexer.search import SearchEngine
from spectra_lexer.output import DisplayEngine
from spectra_lexer.output.node import OUTPUT_FLAGS
from test import get_test_filename


def direct_connect(cmp:Component, subcmp:Component) -> None:
    """ Connect one component directly to another without an engine for basic calls. """
    cmd_dict = dict(subcmp.commands())
    def direct_call(cmd:str, *args, **kwargs) -> callable:
        c = cmd_dict.get(cmd)
        if c:
            return c[0](*args, **kwargs)
    cmp.set_engine_callback(direct_call)


# Create components for the tests in order as we need them.
FILE = FileHandler()
DICT_R = RulesManager()
direct_connect(DICT_R, FILE)


def test_dict_files():
    """ Load and perform basic integrity tests on the individual built-in rules dictionaries. """
    full_dict = {}
    for d in DICT_R._load(DICT_R.files):
        # Check for rules that have identical names (keys)
        conflicts = set(d).intersection(full_dict)
        assert not conflicts, "Dictionary key {} contained in two or more files".format(conflicts)
        full_dict.update(d)


RULES_DICT = DICT_R.load()
LEGAL_FLAG_SET = set().union(MATCH_FLAGS, OUTPUT_FLAGS)


@pytest.mark.parametrize("r", RULES_DICT.values())
def test_rules(r):
    """ Go through each rule and perform extensive integrity checks. """
    # If the entry has flags, verify that all of them are valid.
    if r.flags:
        bad_flags = set(r.flags) - LEGAL_FLAG_SET
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


DICT_T = TranslationsManager()
direct_connect(DICT_T, FILE)
TRANSLATIONS_DICT = DICT_T.load([get_test_filename()])
TEST_TRANSLATIONS = list(TRANSLATIONS_DICT.items())
LEXER = StenoLexer()
LEXER.set_rules(RULES_DICT)
LEXER.need_all_keys = True


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_lexer(trial):
    """ Perform all tests for parsing. It fails if the parser raises an exception or can't match all the keys. """
    keys, word = trial
    result = LEXER.query(keys, word)
    rulemap = result.rulemap
    assert rulemap, "Lexer failed to match all keys on {} -> {}.".format(keys, word)


DISPLAY = DisplayEngine()


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_display(trial):
    """ Produce format for all parsing tests and conduct simple tests. """
    keys, word = trial
    result = LEXER.query(keys, word)
    root = DISPLAY.make_tree(result)
    grapher = DISPLAY._grapher
    # The root node starts in the upper left and has no parent.
    assert grapher.get_node_at(0, 0) is root
    assert root.parent is None
    # Every other node descends from it and is unique.
    all_nodes_list = root.get_descendents()
    all_nodes_set = set(all_nodes_list)
    assert len(all_nodes_list) == len(all_nodes_set)
    # Going the other direction, all nodes except the root must have its parent in the set.
    assert all(node is root or node.parent in all_nodes_set for node in all_nodes_list)
    # The nodes available for interaction must be a subset of this collection.
    assert all_nodes_set >= set(grapher._formatter._format_dict)


SEARCH = SearchEngine()
SEARCH.new_search_dict(TRANSLATIONS_DICT)


@pytest.mark.parametrize("trial", TEST_TRANSLATIONS)
def test_search(trial):
    """ Go through each loaded test translation and check the search engine for the mapping in both directions. """
    keys, word = trial
    assert SEARCH.get(keys, "forward") == word
    assert keys in SEARCH.get(word, "reverse")
    # Search should return at least the item itself in both directions and in either mode. "
    assert keys in SEARCH.search(keys, None, "forward", False)
    assert word in SEARCH.search(word, None, "reverse", False)
    assert keys in SEARCH.search(re.escape(keys), None, "forward", True)
    assert word in SEARCH.search(re.escape(word), None, "reverse", True)

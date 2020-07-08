""" Main feature tests for the Spectra steno lexer.
    Tests translation search, lexical analysis, and graphical rendering. """

import re

import pytest
from spectra_lexer import Spectra

from . import TEST_TRANSLATIONS

SPECTRA = Spectra.compile()
SPECTRA.search_engine.set_translations(TEST_TRANSLATIONS)
TEST_TRANSLATION_PAIRS = list(TEST_TRANSLATIONS.items())


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATION_PAIRS)
def test_search(keys, letters) -> None:
    """ Go through each loaded test translation and check all search methods. """
    search = SPECTRA.search_engine.search
    assert search(keys, count=2, mode_strokes=True) == {keys: (letters,)}
    assert search(letters, count=2) == {letters: (keys,)}
    assert keys in search(re.escape(keys), count=2, mode_strokes=True, mode_regex=True)
    assert letters in search(re.escape(letters), count=2, mode_regex=True)


RTFCRE_CHARS = set("/-#STKPWHRAO*EUFRPBLGTSDZ")
DELIMS = '/-'


def _verify_analysis(analysis) -> None:
    """ An analysis test fails if the output rule is malformed or the lexer can't match all the keys. """
    assert analysis
    analysis.verify(RTFCRE_CHARS, DELIMS)
    for item in analysis:
        assert not item.child.is_unmatched, f"Lexer failed to match all keys on {analysis.keys} -> {analysis.letters}."


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATION_PAIRS)
def test_analysis(keys, letters) -> None:
    """ Perform tests for analysis and output. """
    analysis = SPECTRA.analyzer.query(keys, letters)
    _verify_analysis(analysis)
    # The graph and board tests currently pass as long as they don't raise.
    graph = SPECTRA.graph_engine.graph(analysis)
    for ref, rule in graph.items():
        assert graph.draw(ref)
        assert graph.draw(ref, intense=True)
        assert SPECTRA.board_engine.draw_keys(rule.keys)
        assert SPECTRA.board_engine.draw_rule(rule)


def test_compound() -> None:
    """ Make sure compound analysis works on full sequences of translations. """
    for i in range(2, len(TEST_TRANSLATION_PAIRS)+1):
        seq = TEST_TRANSLATION_PAIRS[:i]
        compound_rule = SPECTRA.analyzer.compound_query(seq)
        _verify_analysis(compound_rule)
        assert len(list(compound_rule)) == (2 * len(seq) - 1)


def test_index() -> None:
    """ Basic test for examples index generation. Every translation should have at least one entry. """
    examples = SPECTRA.analyzer.compile_index(TEST_TRANSLATION_PAIRS, process_count=1)
    assert {pair for d in examples.values() for pair in d.items()} == set(TEST_TRANSLATION_PAIRS)

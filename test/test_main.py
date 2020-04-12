#!/usr/bin/env python3

""" Unit tests for lexical analysis and graphical rendering. """

import pytest

from spectra_lexer.base import Spectra

from .base import TEST_TRANSLATIONS


# Create all test resources using default assets.
ENGINE = Spectra().build_engine()


@pytest.mark.parametrize("keys, letters", TEST_TRANSLATIONS.items())
def test_analysis(keys, letters) -> None:
    """ The parsing tests fail if the lexer can't match all the keys. """
    analysis = ENGINE.analyze(keys, letters)
    assert analysis
    for item in analysis:
        assert not item.child.is_unmatched, f"Lexer failed to match all keys on {keys} -> {letters}."
    # Rule start positions must be non-negative and increasing monotonic.
    positions = [c.start for c in analysis]
    assert positions == sorted(map(abs, positions))
    # Perform test for analysis output. Currently only checks that the output doesn't raise.
    assert ENGINE.display(analysis)

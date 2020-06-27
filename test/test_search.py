""" Unit tests for structures in search package. """

import pytest

from spectra_lexer.search.index import RegexError, SimilarKeyIndex, StripCaseIndex


class _CountAIndex(SimilarKeyIndex[str, int]):
    """ Keys are restricted to whatever types the similarity function uses.
        For testing, the similarity function counts the lowercase a's in the string.
        This means strings with equal numbers of a's will compare as "similar".
        In the key lists, they are sorted by this measure, then standard string sort order applies second. """
    def simfn(self, key:str) -> int:
        return key.count("a")


def test_similar_index() -> None:
    """ Unit tests for the similar-key search class. """
    keys = {"a", "Canada", "a man!?", "^hates^", "lots\nof\nlines",
            "",  "A's don't count, just a's", "AaaAaa, Ʊnićodə!"}
    x = _CountAIndex(keys)

    # "Similar keys", should be all keys with the same number of a's as the input.
    assert x.get_similar_keys("a") == ["A's don't count, just a's", "^hates^", "a"]
    assert x.get_similar_keys("none in here") == ["", "lots\nof\nlines"]
    assert x.get_similar_keys("Havana") == ["Canada"]
    assert x.get_similar_keys("lalalalala") == []

    # Restrict the number of returned values.
    assert x.get_similar_keys("add", 2) == ["A's don't count, just a's", "^hates^"]
    assert x.get_similar_keys("still none of the first English letter", 1) == [""]

    # Add/delete/mutate individual items and make sure order is maintained for search.
    x.remove("^hates^")
    assert x.get_similar_keys("a") == ["A's don't count, just a's", "a"]
    x.insert("----I shall be first!---")
    assert x.get_similar_keys("a") == ["----I shall be first!---", "A's don't count, just a's", "a"]
    x.insert("^hates^")
    assert x.get_similar_keys("a") == ["----I shall be first!---", "A's don't count, just a's", "^hates^", "a"]
    x.remove("----I shall be first!---")

    # For nearby keys, the number of a's don't have to match exactly; just return keys near the one we want.
    assert x.get_nearby_keys("Canada", 2) == ["a man!?", "Canada"]
    assert x.get_nearby_keys("Canada", 5) == ["^hates^", "a", "a man!?", "Canada", "AaaAaa, Ʊnićodə!"]
    assert x.get_nearby_keys("b", 4) == ["", "lots\nof\nlines", "A's don't count, just a's", "^hates^"]
    assert set(x.get_nearby_keys("EVERYTHING", 100)) == keys

    # Random keys must be unique and from the original set. Asking for more than we have should return them all.
    n = len(keys)
    for i in range(n):
        assert set(x.get_random_keys(i)) < keys
    for i in (n, n + 1, n + 100):
        assert set(x.get_random_keys(i)) == keys


def test_string_index() -> None:
    """ Unit tests for the added functionality of the string-based search class. """
    keys = ['beautiful', 'Beautiful', '{^BEAUTIFUL}  ', 'ugly']
    x = StripCaseIndex(keys, ' #{^}')

    # Similarity is based on string equality after removing case and stripping certain characters from the ends.
    assert x.get_similar_keys('beautiful') == ['Beautiful', 'beautiful', '{^BEAUTIFUL}  ']
    assert x.get_similar_keys('{#BEAUtiful}{^}') == ['Beautiful', 'beautiful', '{^BEAUTIFUL}  ']
    assert x.get_similar_keys('') == []

    # Prefix search will return words in sorted order which are supersets of the input starting from
    # the beginning after applying the similarity function. Also stops at the end of the list.
    keys = {'beau', 'beautiful', 'Beautiful', 'beautifully', 'BEAUTIFULLY', 'ugly', 'ugliness'}
    x.clear()
    x.update(keys)
    assert x.prefix_match_keys('beau',   count=4) == ['beau', 'Beautiful', 'beautiful', 'BEAUTIFULLY']
    assert x.prefix_match_keys('UGLY',   count=2) == ['ugly']
    assert x.prefix_match_keys('beauty', count=1) == []

    # Even if a prefix isn't present by itself, the search will return words that contain it
    # going forward from the index where it *would* be found if it was there.
    assert x.prefix_match_keys('beaut', count=3) == ['Beautiful', 'beautiful', 'BEAUTIFULLY']
    assert x.prefix_match_keys('',      count=1) == ['beau']

    # If count is None or not given, prefix search will return all possible supersets in the dictionary.
    assert x.prefix_match_keys('beaut', count=None) == ['Beautiful', 'beautiful', 'BEAUTIFULLY', 'beautifully']
    assert set(x.prefix_match_keys('')) == keys

    # Regex search is straightforward; return up to count entries in order that match the given regular expression.
    # If no regex metacharacters are present, should just be a case-sensitive prefix search.
    assert x.regex_match_keys('beau',          count=4) == ['beau', 'beautiful', 'beautifully']
    assert x.regex_match_keys('beautiful.?.?', count=2) == ['beautiful', 'beautifully']
    assert x.regex_match_keys(' beautiful',    count=3) == []
    assert x.regex_match_keys('(b|u).{3}$',    count=2) == ['beau', 'ugly']
    assert x.regex_match_keys('B',             count=9) == ['Beautiful', 'BEAUTIFULLY']
    assert x.regex_match_keys('.*ly',          count=5) == ['beautifully', 'ugly']

    # If count is None or not given, regex search should just go through the entire list in order.
    assert x.regex_match_keys('.*u.+y', count=None) == ['beautifully', 'ugly']
    assert set(x.regex_match_keys('')) == keys

    # Regex errors still raise even if there are no possible matches.
    with pytest.raises(RegexError):
        x.regex_match_keys('beautiful...an open group(', count=1)
    with pytest.raises(RegexError):
        x.regex_match_keys('an open group with no matches(', count=5)

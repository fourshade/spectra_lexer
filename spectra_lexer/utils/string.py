""" Utility module for string operations which ought to have been built-ins. Pure Python string handling is too slow.
    Even after caching attributes and globals, string object creation and function call overhead will eat you alive. """

import functools


def str_prefix(s:str, sep:str=" ", _split=str.split) -> str:
    """ Return <s> from the start up to the first instance of <sep>. If <sep> is not present, return all of <s>. """
    return _split(s, sep, 1)[0]


def str_suffix(s:str, sep:str=" ", _rsplit=str.rsplit) -> str:
    """ Return <s> from the end up to the last instance of <sep>. If <sep> is not present, return all of <s>. """
    return _rsplit(s, sep, 1)[-1]


def _remove_char(s:str, c:str, _replace=str.replace) -> str:
    """ Return a copy of <s> with the character <c> removed starting from the left. """
    return _replace(s, c, "", 1)


def str_without(s:str, chars, _reduce=functools.reduce) -> str:
    """ Return <s> with each of the characters in <chars> removed, starting from the left. """
    # Fast path: if the characters are a direct prefix, just cut it off.
    prefix_length = len(chars)
    if s[:prefix_length] == chars:
        return s[prefix_length:]
    # Otherwise, each key must be removed individually.
    return _reduce(_remove_char, chars, s)

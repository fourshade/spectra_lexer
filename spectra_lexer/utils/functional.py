""" Utility module for functional operations. """

import functools


def nop(*args, **kwargs) -> None:
    """ ... """


def compose(*funcs):
    """ Compose a series of n callables to create a single callable that combines
        their effects, calling each one in turn with the result of the previous.
        The order is defined such that the first callable in the sequence receives
        the original arguments, i.e. compose(h, g, f)(*args) evaluates to f(g(h(*args))). """
    # Degenerate case: composition of 0 functions = identity function (single argument only).
    if not funcs:
        return lambda x: x
    # Feed the arguments to the first function and chain from there.
    f_first, *f_rest = funcs
    def composed(*args, **kwargs):
        result = f_first(*args, **kwargs)
        for f in f_rest:
            result = f(result)
        return result
    return composed


def memoize(fn):
    """ Decorator to memoize a function using the fastest method possible for unlimited size.
        There used to be Python tricks for fast caching, but functools.lru_cache now has a C implementation.
        The unbounded (non-LRU) case outperforms any cache system written in pure Python now. """
    return functools.lru_cache(maxsize=None)(fn)

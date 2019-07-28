""" Module for generic utility functions that could be useful in many applications.
    Most are ruthlessly optimized, with attribute lookups and globals cached in default arguments. """

from functools import partial
from itertools import starmap
from multiprocessing import cpu_count, Pool
import sys
from traceback import print_exc
from typing import Callable, Iterable


def traverse(obj:object, next_attr:str="next", sentinel:object=None):
    """ Traverse a linked-list type structure, following a chain of attribute references
        and yielding values until either the sentinel is found or the attribute is not.
        Reference loops will cause the generator to yield items forever. """
    while obj is not sentinel:
        yield obj
        obj = getattr(obj, next_attr, sentinel)


def recurse(obj:Iterable, max_level:int=-1):
    """ Starting with an iterable container object that can contain other similar objects,
        yield that object, then recursively yield objects from its contents, depth-first.
        Recursion stops if the current object is not iterable.
        If <max_level> is not negative, it will also stop after that many levels.
        Reference loops will cause the generator to recurse up to the recursion limit. """
    yield obj
    if max_level:
        try:
            for item in obj:
                yield from recurse(item, max_level - 1)
        except TypeError:
            return


def recurse_attr(obj:object, attr:str, max_level:int=-1):
    """ Recurse over objects that have contents in an iterable attribute. """
    yield obj
    if max_level:
        for item in getattr(obj, attr, ()):
            yield from recurse_attr(item, attr, max_level - 1)


def par_starmap(func:Callable, iterable:Iterable[tuple], *args, processes:int=None, **kwargs) -> list:
    """ Equivalent of itertools.starmap using multiprocessing. Returns a list instead of an iterator.

        Use of multiprocessing is very error-prone due to its requirement to recursively pickle every object associated
        with the provided callable in order to send the entire state to each process. If that callable is a method,
        it must pickle both the instance and the class, which may have many dependencies, all of which must themselves
        be picklable, and so on. Manual pickle handling with __getstate__ and __setstate__ can mitigate this, but some
        objects will never be picklable due to dependence on external resources (i.e. open files). Because of this,
        any time multiprocessing fails, we simply fall back to single-process computation and print a message to stderr.

        Another caveat is that the multiprocessing map operations internally consume the entire iterable to make a list
        before sending the pieces to each process. This means any expensive computations involved in lazy iteration are
        performed *before* any work is done in parallel. However, if we want the possibility of retrying the computation
        with a single process, we have to evaluate the iterable and save the results to a list ourselves anyway. """
    # Extra arguments are treated as partials applying to *every* call.
    if args or kwargs:
        func = partial(func, *args, **kwargs)
    # If not specified, the number of processes defaults to the number of CPU cores.
    processes = processes or cpu_count() or 1
    if processes > 1:
        # Make a list out of the iterable (which may be one-time use) in case we have to retry with one process.
        iterable = list(iterable)
        try:
            # Use Pool.starmap() to call a function on each argument tuple in parallel.
            with Pool(processes) as pool:
                return pool.starmap(func, iterable)
        except Exception:
            print_exc()
            print("Parallel operation failed. Trying with a single process...", file=sys.stderr)
    # With only one process (or a failed process pool), use ordinary starmap.
    return list(starmap(func, iterable))

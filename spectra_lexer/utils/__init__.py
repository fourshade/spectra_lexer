""" Package for generic utility functions that could be useful in many applications.
    Most are ruthlessly optimized, with attribute lookups and globals cached in default arguments.
    They are sorted into modules based on operation type, but are all accessible from the top-level package. """

from .functional import *
from .iteration import *
from .parallel import *
from .string import *

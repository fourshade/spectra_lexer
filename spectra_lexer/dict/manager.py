from typing import Iterable

from spectra_lexer import Component, on, fork, pipe
from spectra_lexer.utils import merge


class ResourceManager(Component):

    R_TYPE: str


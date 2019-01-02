from typing import Iterable

from spectra_lexer import SpectraComponent
from spectra_lexer.dict import DictManager
from spectra_lexer.engine import SpectraEngine
from spectra_lexer.file import FileHandler
from spectra_lexer.lexer import StenoLexer
from spectra_lexer.node import NodeTreeGenerator
from spectra_lexer.system import SystemModule
from spectra_lexer.text import CascadedTextFormatter


class SpectraApplication:
    """ Base class for fundamental operations of the Spectra lexer involving keys, rules, and nodes. """

    def __init__(self, *components:SpectraComponent):
        """ Initialize the engine and connect everything starting from the base components. """
        all_components = [SystemModule(), FileHandler(), DictManager(), StenoLexer(),
                          NodeTreeGenerator(), CascadedTextFormatter(), *components]
        self.engine = SpectraEngine()
        for c in all_components:
            self.engine.connect(c)

    def start(self, argv:Iterable[str]=()) -> None:
        """ Load the initial rule set. """
        self.engine.send("configure", argv)
        self.engine.send("file_load_builtin_rules")

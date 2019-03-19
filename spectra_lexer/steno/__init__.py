""" Package for the steno components of Spectra. These handle operations related to steno rules and translations. """
class basic:
    from .data import RulesManager, TranslationsManager, SVGManager, IndexManager
    from .lexer import StenoLexer
class interactive:
    from .board import BoardRenderer
    from .graph import GraphRenderer
    from .search import SearchEngine
globals().update({**vars(basic), **vars(interactive)})

""" Package for the core components of Spectra. These handle operations required for the most basic functionality. """

from . import config, file, lexer, parallel, rules, translations

COMPONENTS = [parallel.ParallelExecutor,
              file.FileHandler,
              config.ConfigManager,
              rules.RulesManager,
              translations.TranslationsManager,
              lexer.StenoLexer]

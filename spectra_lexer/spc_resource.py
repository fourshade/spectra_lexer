from functools import wraps
from typing import Callable, Any

from spectra_lexer.board.defs import StenoBoardDefinitions
from spectra_lexer.resource.json import JSONDictionaryIO
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleList, StenoRuleParser
from spectra_lexer.resource.translations import TranslationsDict, ExamplesDict


class ResourceIOError(Exception):
    """ General exception for any resource IO or decoding error. """


def try_load(func:Callable) -> Callable:
    """ Decorator to re-raise I/O and parsing exceptions with more general error messages for the end-user. """
    @wraps(func)
    def load(self, filename:str) -> Any:
        try:
            return func(self, filename)
        except OSError as e:
            raise ResourceIOError(filename + ' is inaccessible or missing.') from e
        except (TypeError, ValueError) as e:
            raise ResourceIOError(filename + ' is not formatted correctly.') from e
        except Exception as e:
            raise ResourceIOError(filename + ' is incomplete or corrupt.') from e
    return load


class StenoResourceIO:
    """ Top-level IO for steno resources. All structures are parsed from JSON in some form.
        Built-in assets include a key layout, rules, and board graphics. """

    def __init__(self, io:JSONDictionaryIO=None) -> None:
        self._io = io or JSONDictionaryIO()  # I/O for JSON/CSON files.

    @try_load
    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load and verify a steno key layout from CSON. """
        d = self._io.load_json_dict(filename)
        keymap = StenoKeyLayout(**d)
        keymap.verify()
        return keymap

    @try_load
    def load_rules(self, filename:str, keymap:StenoKeyLayout=None) -> StenoRuleList:
        """ Load steno rules from CSON. A keymap is required to perform verification. """
        d = self._io.load_json_dict(filename)
        parser = StenoRuleParser()
        for name, data in d.items():
            parser.add_json_data(name, data)
        rules = parser.parse()
        if keymap is not None:
            valid_rtfcre = keymap.valid_rtfcre()
            delimiters = {keymap.separator_key(), keymap.divider_key()}
            for rule in rules:
                rule.verify(valid_rtfcre, delimiters)
        return rules

    @try_load
    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load and verify steno board graphics definitions from CSON. """
        d = self._io.load_json_dict(filename)
        board_defs = StenoBoardDefinitions(**d)
        board_defs.verify()
        return board_defs

    @try_load
    def _load_json_translations(self, filename:str) -> TranslationsDict:
        """ Load RTFCRE steno translations from a JSON file. """
        return self._io.load_json_dict(filename)

    def load_json_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            d = self._load_json_translations(filename)
            translations.update(d)
        return translations

    @try_load
    def load_json_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file formatted as a dict of dicts. """
        examples = self._io.load_json_dict(filename)
        for v in examples.values():
            if not isinstance(v, dict):
                raise TypeError(filename + ' does not contain a nested string dictionary.')
        return examples

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. Key sorting helps some algorithms run faster.
            ensure_ascii=False is required to preserve Unicode symbols. """
        self._io.save_json_dict(filename, examples)

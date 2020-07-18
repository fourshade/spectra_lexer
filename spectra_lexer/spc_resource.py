from spectra_lexer.board.defs import StenoBoardDefinitions
from spectra_lexer.resource.json import JSONDictionaryIO
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleList, StenoRuleParser
from spectra_lexer.resource.translations import ExamplesDict, TranslationsDict


class StenoResourceIO:
    """ Top-level IO for steno resources. All structures are parsed from JSON in some form.
        Built-in assets include a key layout, rules, and board graphics. """

    def __init__(self, io:JSONDictionaryIO=None) -> None:
        self._io = io or JSONDictionaryIO()  # I/O for JSON/CSON files.

    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load and verify a steno key layout from CSON. """
        d = self._io.load_json_dict(filename)
        keymap = StenoKeyLayout(**d)
        keymap.verify()
        return keymap

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

    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load and verify steno board graphics definitions from CSON. """
        d = self._io.load_json_dict(filename)
        board_defs = StenoBoardDefinitions(**d)
        board_defs.verify()
        return board_defs

    def load_json_translations(self, *filenames:str) -> TranslationsDict:
        """ Load and merge RTFCRE steno translations from JSON files. """
        translations = {}
        for filename in filenames:
            d = self._io.load_json_dict(filename)
            translations.update(d)
        return translations

    def save_json_translations(self, filename:str, translations:TranslationsDict) -> None:
        """ Save RTFCRE steno translations as a dict in JSON. """
        self._io.save_json_dict(filename, translations)

    def load_json_examples(self, filename:str) -> ExamplesDict:
        """ Load an examples index from a JSON file formatted as a dict of dicts. """
        examples = self._io.load_json_dict(filename)
        for v in examples.values():
            if not isinstance(v, dict):
                raise TypeError(filename + ' does not contain a nested string dictionary.')
        return examples

    def save_json_examples(self, filename:str, examples:ExamplesDict) -> None:
        """ Save an examples index as a dict of dicts in JSON. """
        self._io.save_json_dict(filename, examples)

from typing import List

from spectra_lexer.resource.board import StenoBoardDefinitions
from spectra_lexer.resource.json import JSONDictionaryIO
from spectra_lexer.resource.keys import StenoKeyLayout
from spectra_lexer.resource.rules import StenoRuleFactory, StenoRule
from spectra_lexer.resource.sub import TextSubstitutionParser
from spectra_lexer.resource.translations import ExamplesDict, TranslationsDict


class StenoRuleParser:
    """ Converts steno rules from JSON arrays to StenoRule objects.
        In order to recursively resolve references, all rule data should be added before any parsing is done. """

    # Acceptable string values for rule flags, as read from JSON.
    FLAGS = {"REF":  'is_reference',
             "STRK": 'is_stroke',
             "WORD": 'is_word',
             "RARE": 'is_rare',
             "INV":  'is_inversion',
             "LINK": 'is_linked'}

    def __init__(self, factory:StenoRuleFactory, sub_parser:TextSubstitutionParser) -> None:
        self._factory = factory        # Creates steno rules from JSON data.
        self._sub_parser = sub_parser  # Parser specifically for the pattern field.
        self._rule_data = {}           # Dict of other steno rule data fields from JSON.
        self._rule_memo = {}           # Memo of finished rules.

    def add_json_data(self, r_id:str, fields:list) -> None:
        """ Add JSON data for a single rule. The fields, in order, are:
            keys:    RTFCRE formatted string of steno strokes.
            pattern: English text pattern string, consisting of raw letters as well as references to other rules.
            flags:   Optional sequence of flag strings.
            info:    Optional description string for when the rule is displayed in the GUI. """
        try:
            keys, pattern, *optional = fields
        except ValueError as e:
            raise ValueError(f"Not enough data fields for rule {r_id}") from e
        flags = optional.pop(0) if optional else ()
        info = optional.pop(0) if optional else "No description"
        if optional:
            raise ValueError(f"Too many data fields for rule {r_id}: extra = {optional}")
        alt = ""
        if "(" not in pattern and "|" in pattern:
            pattern, alt = pattern.split("|", 1)
        self._sub_parser.add_mapping(r_id, pattern)
        self._rule_data[r_id] = [keys, flags, info, alt]

    def parse(self, r_id:str) -> StenoRule:
        """ Return a rule by ID if finished, else parse it recursively. """
        memo = self._rule_memo
        if r_id in memo:
            return memo[r_id]
        keys, flags, info, alt = self._rule_data[r_id]
        sub_result = self._sub_parser.parse(r_id)
        self._factory.push()
        for sub in sub_result.subs:
            child = self.parse(sub.ref)
            self._factory.connect(child, sub.start, sub.length)
        letters = sub_result.text
        flag_kwargs = {self.FLAGS[s]: True for s in flags}
        rule = memo[r_id] = self._factory.build(keys, letters, info, alt, r_id, **flag_kwargs)
        return rule


StenoRuleList = List[StenoRule]


class StenoResourceIO:
    """ Top-level IO for steno resources. All structures are parsed from JSON in some form.
        Built-in assets include a key layout, rules, and board graphics. """

    def __init__(self, rule_factory:StenoRuleFactory) -> None:
        self._rule_factory = rule_factory  # Steno rule object factory.
        self._io = JSONDictionaryIO()      # I/O for JSON/CSON files.

    def load_keymap(self, filename:str) -> StenoKeyLayout:
        """ Load a steno key layout from CSON. """
        d = self._io.load_json_dict(filename)
        return StenoKeyLayout(**d)

    def load_rules(self, filename:str) -> StenoRuleList:
        """ Load a list of steno rules from CSON. """
        d = self._io.load_json_dict(filename)
        sub_parser = TextSubstitutionParser()
        parser = StenoRuleParser(self._rule_factory, sub_parser)
        for name, data in d.items():
            parser.add_json_data(name, data)
        return [parser.parse(name) for name in d]

    def load_board_defs(self, filename:str) -> StenoBoardDefinitions:
        """ Load steno board graphics definitions from CSON. """
        d = self._io.load_json_dict(filename)
        return StenoBoardDefinitions(**d)

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

import re
from typing import Dict, NamedTuple, Tuple

from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMap, StenoRule

# Available bracket pairs for parsing rules.
LEFT_BRACKETS = r'\(\['
RIGHT_BRACKETS = r'\)\]'

# Rule substitutions must match a left bracket, one or more non-brackets, and a right bracket.
SUBRULE_RX = re.compile(r'[{}]'.format(LEFT_BRACKETS) +
                        r'[^{0}{1}]+?'.format(LEFT_BRACKETS, RIGHT_BRACKETS) +
                        r'[{}]'.format(RIGHT_BRACKETS))


class RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str              # RTFCRE formatted series of steno strokes.
    pattern: str           # English text pattern, consisting of raw letters as well as references to other rules.
    flag_str: str = ""     # Optional pipe-delimited series of flags.
    description: str = ""  # Optional description for when the rule is displayed in the GUI.
    example_str: str = ""  # Optional pipe-delimited series of example translations using this rule.


def raw_rule_dict(src:dict) -> Dict[str, RawRule]:
    """ Make a namedtuple-based raw rules dictionary from an unformatted dict loaded directly from disk. """
    if src is None:
        return {}
    return {k: RawRule(*v) for (k, v) in src.items()}


class StenoRuleDict(Dict[str, StenoRule]):
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    _src_dict: Dict[str, RawRule]  # Keep the source dict in the instance to avoid passing it everywhere.

    def __init__(self, src_dict:dict=None):
        """ Top level parsing method. Goes through source JSON dict and parses every entry using mutual recursion. """
        # Unpack rules from source dictionary. If the data isn't in namedtuple form, convert it.
        self._src_dict = raw_rule_dict(src_dict)
        # Parse all rules from source dictionary into this one, indexed by name.
        # This will parse entries in a semi-arbitrary order, so make sure not to redo any.
        super().__init__()
        for k in self._src_dict.keys():
            if k not in self:
                self._parse(k)

    def _parse(self, k:str) -> None:
        """ Parse a source dictionary rule into a StenoRule object. """
        raw_rule = self._src_dict[k]
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, built_map = self._substitute(raw_rule.pattern)
        # The keys must be converted from RTFCRE form into lexer form.
        keys = StenoKeys.from_rtfcre(raw_rule.keys)
        # Parse the flag string and add key flags as ending rules.
        flags = frozenset(filter(None, raw_rule.flag_str.split("|")))
        if flags:
            for r in StenoRule.key_rules(flags):
                built_map.add_special(r, len(letters))
        description = raw_rule.description
        # For now, just include examples as a line after the description joined with commas.
        if raw_rule.example_str:
            description = "{}\n({})".format(description, raw_rule.example_str.replace("|", ", "))
        # The built rulemap must be frozen before final inclusion in a rule.
        self[k] = StenoRule(keys, letters, flags, description, built_map.freeze())

    def _substitute(self, pattern:str) -> Tuple[str, RuleMap]:
        """
        From a rule's raw pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in the letters: (.d)e(.s) -> des. For [] brackets, the letters and reference are given separately.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references will crash the program.
        """
        built_map = RuleMap()
        m = SUBRULE_RX.search(pattern)
        while m:
            # For every child rule, strip the parentheses to get the dict key (and the letters for [] rules).
            rule_str = m.group()
            if rule_str[0] == '(':
                letters = None
                rule_key = rule_str[1:-1]
            else:
                (letters, rule_key) = rule_str[1:-1].split("|", 1)
            # Look up the child rule and parse it if it hasn't been yet. Even if we aren't using its letters,
            # we still need to parse it at this stage so that the correct reference goes in the rulemap.
            if rule_key not in self:
                if rule_key not in self._src_dict:
                    raise KeyError("Illegal reference: {} in {}".format(rule_key, pattern))
                self._parse(rule_key)
            rule = self[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if not letters:
                letters = rule.letters
            built_map.add(rule, m.start(), len(letters))
            pattern = pattern.replace(rule_str, letters)
            m = SUBRULE_RX.search(pattern)
        return pattern, built_map

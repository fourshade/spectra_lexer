import re
from typing import Dict, Iterable, List, NamedTuple, Sequence, Tuple

from spectra_lexer.dict.manager import ResourceManager
from spectra_lexer.keys import StenoKeys
from spectra_lexer.rules import RuleMapItem, StenoRule

# Available bracket pairs for parsing rules.
LEFT_BRACKETS = r'\(\['
RIGHT_BRACKETS = r'\)\]'

# Rule substitutions must match a left bracket, one or more non-brackets, and a right bracket.
SUBRULE_RX = re.compile(r'[{}]'.format(LEFT_BRACKETS) +
                        r'[^{0}{1}]+?'.format(LEFT_BRACKETS, RIGHT_BRACKETS) +
                        r'[{}]'.format(RIGHT_BRACKETS))

# Resource glob pattern for the built-in JSON-based rules files.
_RULES_ASSET_PATTERN = ":/*.cson"


class RawRule(NamedTuple):
    """ Data structure for raw string fields read from each line in a JSON rules file. """
    keys: str              # RTFCRE formatted series of steno strokes.
    pattern: str           # English text pattern, consisting of raw letters as well as references to other rules.
    flag_str: str = ""     # Optional pipe-delimited series of flags.
    description: str = ""  # Optional description for when the rule is displayed in the GUI.
    example_str: str = ""  # Optional pipe-delimited series of example translations using this rule.


class RulesManager(ResourceManager):
    """ Class which takes a source dict of raw JSON rule entries with nested references and parses
        them recursively to get a final dict of independent steno rules indexed by internal name. """

    ROLE = "dict_rules"
    files = [_RULES_ASSET_PATTERN]

    _src_dict: Dict[str, RawRule]    # Keep the source dict in the instance to avoid passing it everywhere.
    _dst_dict: Dict[str, StenoRule]  # Same case for the destination dict. This one also needs to be kept.
    _rev_dict: Dict[StenoRule, str]  # Same case for the reverse reference dict when converting back to JSON form.

    def parse(self, src_dict:Dict[str, str]) -> Dict[str, StenoRule]:
        """ Top level parsing method. Goes through source JSON dict and parses every entry using mutual recursion. """
        # Unpack rules from source dictionary. If the data isn't in namedtuple form, convert it.
        self._src_dict = {k: RawRule(*v) for (k, v) in src_dict.items()}
        # Parse all rules from source dictionary into this one, indexed by name.
        # This will parse entries in a semi-arbitrary order, so make sure not to redo any.
        self._dst_dict = {}
        for k in self._src_dict.keys():
            if k not in self._dst_dict:
                self._parse(k)
        # Return only the rules themselves. Components such as the lexer don't care about the names.
        # Multiple components may want to use these, so the iterable must be reusable (i.e. a list).
        return self._dst_dict

    def _parse(self, k:str) -> None:
        """ Parse a source dictionary rule into a StenoRule object. """
        raw_rule = self._src_dict[k]
        # We have to substitute in the effects of all child rules. These determine the final letters and rulemap.
        letters, built_map = self._substitute(raw_rule.pattern)
        # The keys must be converted from RTFCRE form into lexer form.
        keys = StenoKeys.from_rtfcre(raw_rule.keys)
        # Parse the flag string into a set and keep the description string directly.
        flags = frozenset(filter(None, raw_rule.flag_str.split("|")))
        description = raw_rule.description
        # For now, just include examples as a line after the description joined with commas.
        if raw_rule.example_str:
            description = "{}\n({})".format(description, raw_rule.example_str.replace("|", ", "))
        # The built rulemap must be frozen before final inclusion in a rule.
        self._dst_dict[k] = StenoRule(keys, letters, flags, description, tuple(built_map))

    def _substitute(self, pattern:str) -> Tuple[str, List[RuleMapItem]]:
        """
        From a rule's raw pattern string, find all the child rule references in brackets and make a map
        so the format code can break it down again if needed. For those in () brackets, we must substitute
        in the letters: (.d)e(.s) -> des. For [] brackets, the letters and reference are given separately.

        Only already-finished rules from the results dict can be directly substituted. Any rules that are
        not finished yet will still contain their own child rules in brackets. If we find one of these,
        we have to parse it first in a recursive manner. Circular references will crash the program.
        """
        built_map = []
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
            if rule_key not in self._dst_dict:
                if rule_key not in self._src_dict:
                    raise KeyError("Illegal reference: {} in {}".format(rule_key, pattern))
                self._parse(rule_key)
            rule = self._dst_dict[rule_key]
            # Add the rule to the map and substitute in the letters if necessary.
            if not letters:
                letters = rule.letters
            built_map.append(RuleMapItem(rule, m.start(), len(letters)))
            pattern = pattern.replace(rule_str, letters)
            m = SUBRULE_RX.search(pattern)
        return pattern, built_map

    def inv_parse(self, rules:Iterable[StenoRule]) -> Dict[str, RawRule]:
        """ From a bare iterable of rules (generally from the lexer), make a new raw dict using auto-generated
            reference names and substituting rules in each rulemap for their letters. """
        # The previous dict must be reversed one-to-one to look up names given rules.
        self._rev_dict = {v: k for (k, v) in self._dst_dict.items()}
        return {str(r): self._inv_parse(r) for r in rules}

    def _inv_parse(self, r:StenoRule) -> RawRule:
        """ Convert a StenoRule object into a raw series of fields. """
        # The keys must be converted to RTFCRE form.
        keys = r.keys.to_rtfcre()
        # The pattern must be deduced from the letters, the rulemap, and the reference dict.
        pattern = self._inv_substitute(r.letters, r.rulemap)
        # Join the flags into a string. The description is copied verbatim.
        flag_str = "|".join(r.flags)
        description = r.desc
        # There are no examples in a generated rule.
        example_str = ""
        return RawRule(keys, pattern, flag_str, description, example_str)

    def _inv_substitute(self, letters:str, rulemap:Sequence[RuleMapItem]) -> str:
        """ For each mapped rule with a name reference, replace the mapped letters with the reference. """
        # Go from right to left to preserve indexing.
        for item in reversed(rulemap):
            r = item.rule
            # Some rules aren't named or are special. Don't show these in the pattern.
            name = self._rev_dict.get(r)
            if not name:
                continue
            # Some rules take up no letters. Don't add these even if references exist.
            start = item.start
            end = start + item.length
            if start == end:
                continue
            # Replace the letters this rule takes up with a standard parenthesized reference.
            letters = letters[:start] + "({})".format(name) + letters[end:]
        return letters

from itertools import product, starmap
from typing import Iterable, List

from spectra_lexer import on, SpectraComponent
from spectra_lexer.keys import KEY_SEP, KEY_STAR, StenoKeys
from spectra_lexer.lexer.match import LexerRuleMatcher
from spectra_lexer.rules import RuleMap, StenoRule, MutableRuleMap


class StenoLexer(SpectraComponent):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    """

    _rule_matcher: LexerRuleMatcher = None  # The only state the lexer needs is the rule-matching dictionary.

    @on("new_rules")
    def set_rules(self, rules:Iterable[StenoRule]) -> None:
        """ Take a sequence of rules parsed from a file and sort them into categories for the lexer. """
        self._rule_matcher = LexerRuleMatcher(rules)

    @on("new_query")
    def query(self, keys:str, word:str) -> StenoRule:
        """ Return the best rule that maps the given key string to the given word. Send it to the engine as well. """
        rule = self._generate_rule(keys, word)
        self.engine_call("new_lexer_result", rule)
        return rule

    @on("new_query_product")
    def query_best_product(self, keys:Iterable[str], words:Iterable[str]) -> StenoRule:
        """ As arguments, take iterables of keys and words and test every possible pairing.
            Return the best rule out of all combinations. Send it to the engine as well. """
        rule = StenoRule.best_rule(starmap(self._generate_rule, product(keys, words)))
        self.engine_call("new_lexer_result", rule)
        return rule

    def _generate_rule(self, keys:str, word:str) -> StenoRule:
        """ Given a key string and a matching translation, return the best possible rule relating the two. """
        # Thoroughly cleanse and parse the key string(s) (user strokes cannot be trusted).
        keys = StenoKeys.cleanse(keys)
        # Collect all valid rulemaps (that aren't optimized away) for the given keys and word.
        maps = self._generate_maps(keys, word)
        # Find the highest ranked rulemap according to how accurately it (probably) mapped the stroke
        # to the translation (or an empty map if none). Make a rule out of the result and return it.
        best_map = RuleMap.best_map(maps)
        return StenoRule.from_lexer_result(keys, word, best_map)

    def _generate_maps(self, keys:StenoKeys, word:str) -> List[RuleMap]:
        """
        Given a string of parsed steno keys and a matching translation, use steno rules to match keys to printed
        characters in order to generate a list of complete rule maps that could possibly produce the translation.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        maps = []
        best_letters = 0
        get_rule_matches = self._rule_matcher.match
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, MutableRuleMap())]
        while stack:
            # Take the next search path off the stack.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            # If we only have a star left at the end of a stroke, consume it and try to guess its meaning.
            if test_keys and test_keys[0] == KEY_STAR and (len(test_keys) == 1 or test_keys[1] == KEY_SEP):
                rulemap.add_key_rules({_decipher_star(test_keys, word, rulemap)}, wordptr)
                test_keys = test_keys.without(KEY_STAR)
            # If we end up with a stroke separator at the pointer, consume it and add the rule.
            if test_keys and test_keys[0] == KEY_SEP:
                rulemap.add_separator(wordptr)
                test_keys = test_keys.without(KEY_SEP)
            # If unmatched keys remain, attempt to match them to rules in steno order.
            # We assume every rule matched here MUST consume at least one key and one letter.
            if test_keys:
                # We have a complete stroke if we haven't matched anything or the last match was a stroke separator.
                is_full_stroke = (not rulemap or rulemap.ends_with_separator())
                # We have a complete word if the word pointer is 0 or sitting on a space.
                is_full_word = (wordptr == 0 or (test_word and test_word[0] == ' '))
                # Calculate how many letters we could possibly skip and still be in the running for best map.
                space_left = len(test_word) - (best_letters - lc)
                # Get the rules that would work as the next match in order from last found (least keys) to first found
                # (most keys). This helps us find dense maps first so we can eliminate later ones quickly on space.
                for r in reversed(get_rule_matches(test_keys, test_word, is_full_stroke, is_full_word)):
                    # Find the first index of each match. This is also how many characters were skipped.
                    i = test_word.find(r.letters)
                    # Filter out cases that no longer have enough space left to beat or tie the best map.
                    if space_left < i:
                        continue
                    # Make a copy of the current map and add the new rule + its location in the complete word.
                    word_len = len(r.letters)
                    new_map = MutableRuleMap(rulemap)
                    new_map.add_child(r, wordptr + i, word_len)
                    # Push a stack item with the new map, and with the matched keys and letters removed.
                    word_inc = word_len + i
                    stack.append((test_keys.without(r.keys), test_word[word_inc:],
                                  wordptr + word_inc, lc + word_len, new_map))
            else:
                # If we got here, we finished a legitimate mapping that could be better than anything we've got.
                # Save the best letter count so we can reject bad maps early.
                maps.append(rulemap)
                best_letters = max(best_letters, lc)
        return maps


def _decipher_star(keys:StenoKeys, word:str, rulemap:RuleMap) -> str:
    """ Try to guess the meaning of an asterisk from the remaining keys, the full word, and the current rulemap.
        Return the flag value for the best-guess rule, or the undecided rule if nothing matches. """
    # If the word contains a period, it's probably an abbreviation (it must have letters to make it this far).
    if "." in word:
        return "*:AB"
    # If the word has uppercase letters in it, it's probably a proper noun.
    if word != word.lower():
        return "*:PR"
    # If we have a separator key left but no recorded matches, we are at the beginning of a multi-stroke word.
    # If we have recorded separators but none left in the keys, we are at the end of a multi-stroke word.
    # Neither = single-stroke word, both = middle of multi-stroke word, just one = prefix/suffix.
    if (KEY_SEP in keys) ^ any(KEY_SEP in r.keys for r in rulemap.rules()):
        return "*:PS"
    return "*:??"

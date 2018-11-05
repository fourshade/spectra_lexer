from typing import Collection, List, Sequence, Tuple, Union

from spectra_lexer.keys import StenoKeys, KEY_SEP, KEY_STAR
from spectra_lexer.output import LexerOutput
from spectra_lexer.rules.lexer_dict import LexerDictionary
from spectra_lexer.rules.rules import RuleMap


class StenoLexer(object):
    """
    The main lexer engine. Uses trial-and-error stack based analysis to gather all possibilities for steno
    patterns it can find, then sorts among them to find what it considers the most likely to be correct.
    It is one of the only classes that should be exposed to the GUI and console script.
    """

    _rule_dict: LexerDictionary  # The only state the lexer needs is the rule-matching dictionary.

    def __init__(self, *filenames:str):
        self._rule_dict = LexerDictionary(*filenames)

    def parse(self, key_strings:Union[str,Collection[str]], word:str) -> LexerOutput:
        """ Given a key string (or collection of key strings) with possible series' of strokes and a
            matching translation, use a series of steno rules to match steno keys to printed characters.
            Return only the best-fit rule out of every possibility. """
        # Thoroughly cleanse and parse each key string (user strokes cannot be trusted).
        if isinstance(key_strings, str):
            keys_list = [StenoKeys.cleanse(key_strings)]
        else:
            keys_list = list(map(StenoKeys.cleanse, key_strings))
        # Collect all possible rule maps and their matching keys for the given word into tuples.
        results = []
        for keys in keys_list:
            for m in self._match_rules(keys, word):
                results.append((keys, word, m))
        # Return a blank rule map (with only the first set of keys and the word) if we found nothing.
        # Otherwise keep only the highest ranked rule map according to how accurately it (probably) mapped the stroke.
        if not results:
            params_out = (keys_list[0], word, RuleMap())
        else:
            params_out = max(results, key=_rank_value)
        return LexerOutput(*params_out)

    def _match_rules(self, keys:StenoKeys, word:str) -> List[RuleMap]:
        """
        Return a list of all complete rule maps that could possibly produce the given word.
        A "complete" map is one that matches every one of the given keys to a rule.

        The stack is a simple list of tuples, each containing the state of the lexer at some point in time.
        The lexer state includes: keys unmatched, letters unmatched/skipped, position in the full word,
        number of letters matched, and the current rule map. These completely define the lexer's progress.
        """
        maps = []
        best_letters = 0
        # Initialize the stack with the start position ready at the bottom and start processing.
        # To match sentence beginnings and proper names, the word must be converted to lowercase.
        stack = [(keys, word.lower(), 0, 0, RuleMap())]
        while stack:
            # Take the next search path off the stack.
            test_keys, test_word, wordptr, lc, rulemap = stack.pop()
            # If we only have a star left at the end of a stroke, consume it and try to guess its meaning.
            if test_keys and test_keys[0] == KEY_STAR and (len(test_keys) == 1 or test_keys[1] == KEY_SEP):
                rulemap.add_key_rules([_decipher_star(test_keys, word, rulemap)], wordptr)
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
                # Get the rules that would work as the next match.
                rule_matches = self._rule_dict.match(test_keys, test_word, is_full_stroke, is_full_word)
                # Find the first index of each match.
                word_indices = [test_word.find(r.letters) for r in rule_matches]
                # Combine rules and their match indices, filtering out cases that can't beat or tie the best map.
                space_left = len(test_word) - (best_letters - lc)
                stack_additions = [(i, r) for (i, r) in zip(word_indices, rule_matches) if space_left >= i]
                # In order from last found (least keys) to first found (most keys), add to the stack.
                for (i, r) in reversed(stack_additions):
                    # Make a copy of the current map and add the new rule + its location in the complete word.
                    word_len = len(r.letters)
                    new_map = RuleMap(rulemap)
                    new_map.add_child(r, wordptr + i, word_len)
                    # Push a stack item with the new map, and with the matched keys and letters removed.
                    word_inc = word_len + i
                    stack.append((test_keys.without(r.keys), test_word[word_inc:],
                                  wordptr + word_inc, lc + word_len, new_map))
                else:
                    # This mapping will never be finished. For now, discard it and move on to the next stack item.
                    pass
            else:
                # If we got here, we finished a legitimate mapping.
                # Save the best letter count so we can reject bad maps early.
                best_letters = max(best_letters, lc)
                maps.append(rulemap)
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


def _rank_value(params:Tuple[StenoKeys,str,RuleMap]) -> Sequence[int]:
    """
    Determine the "value" of a rule map for sorting of lexer format. A larger value should reflect
    a more accurate mapping. Rank value is determined by a tuple of these values, in order:
        - least keys unmatched
        - most letters matched
        - fewest child rules
        - end-to-end word coverage
    """
    keys, _, rulemap = params
    return (rulemap.keys_matched() - len(keys),
            rulemap.letters_matched(),
            -len(rulemap),
            rulemap.get_word_coverage())

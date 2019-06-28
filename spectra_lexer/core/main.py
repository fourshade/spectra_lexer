from typing import Callable, List


class Main(dict):
    """ Formal entry point dictionary for an application. Add entries at the module level after defining classes. """

    _DEFAULT: str = None  # Last set default entry point mode.
    _descriptions: list   # List of all description strings.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._descriptions = []

    def add_entry_point(self, func:Callable, mode:str, desc:str="Spectra program.", is_default:bool=False) -> None:
        """ Specify a callable, mode string, description, and whether or not it is the new default. """
        self[mode] = func
        self._descriptions.append(f"{mode} - {desc}")
        # Always set the very first entry point as the "default" default.
        if self._DEFAULT is None or is_default:
            self._DEFAULT = mode

    def __call__(self, mode:str="", *args, **kwargs) -> int:
        """ Make sure the mode matches exactly one entry point callable, then call it and return an exit code.
            With no mode argument (or a blank one), redirect to the default mode. """
        matches = self._get_matches(mode or self._DEFAULT)
        if len(matches) == 1:
            entry_point = self[matches[0]]
            return entry_point(*args, **kwargs)
        if not matches:
            # If nothing matches, display all entry point modes and their description strings.
            print(f'No matches for operation "{mode}". Currently available operations:')
            print("\n".join(self._descriptions))
        else:
            # If there are too many matches, show them and tell the user to add more characters.
            print(f'Operation "{mode}" has multiple matches: {matches}. Use more characters.')
        return -1

    def _get_matches(self, mode:str) -> List[str]:
        """ Get all entry point modes that match the given string up to its last character. """
        if not self:
            raise RuntimeError('No entry points defined. Please check your imports.')
        return [k for k in self if k.startswith(mode)]


main = Main()

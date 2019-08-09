""" Master console script and primary entry point for the Spectra program. """

import sys


class EntryPoints:
    """ Formal entry point dictionary for applications.
        To avoid unnecessary imports (especially when dependencies are different), only strings are used here. """

    _default: str = None  # Last set default entry point mode.
    _paths: dict          # Dict of all entry point module paths by mode.
    _descriptions: list   # List of all description strings.

    def __init__(self):
        self._paths = {}
        self._descriptions = []

    def add(self, module_path:str, mode:str, desc:str="Unknown function.", *, is_default:bool=False) -> None:
        """ At minimum, each entry point requires a module path string and a mode string.
            <module_path> is an absolute Python module path.
            <mode> refers to a callable member of that module, usually a class or function.
            The mode string is also used to choose that entry point from the command line.
            <desc> is shown beside each entry point when the user looks for help.
            <is_default> sets that entry point to be callled when no mode is given at the command line. """
        self._paths[mode] = module_path
        self._descriptions.append(f"{mode} - {desc}")
        # Always set the very first entry point as the "default" default.
        if self._default is None or is_default:
            self._default = mode

    def __call__(self, mode:str=""):
        """ Make sure the mode matches exactly one entry point, then import and return it. Return None on failure.
            With no mode argument (or a blank one), redirect to the default mode. """
        matches = self._get_matches(mode or self._default)
        if len(matches) == 1:
            return self._import_callable(matches[0])
        if not matches:
            # If nothing matches, display all entry point modes and their description strings.
            print(f'No matches for operation "{mode}". Currently available operations:')
            print("\n".join(self._descriptions))
        else:
            # If there are too many matches, show them and tell the user to add more characters.
            print(f'Operation "{mode}" has multiple matches: {matches}. Use more characters.')

    def _get_matches(self, mode:str) -> list:
        """ Get all entry point modes that match the given string up to its last character. """
        if not self._paths:
            raise RuntimeError('No entry points defined. Please check your imports.')
        return [k for k in self._paths if k.startswith(mode)]

    def _import_callable(self, mode:str):
        """ Import the module on the path corresponding to <mode>, then get the callable as an attribute. """
        module_path = self._paths[mode]
        module = __import__(module_path, globals(), locals(), [mode])
        return getattr(module, mode)


entry_points = EntryPoints()
add = entry_points.add

add("spectra_lexer.console",  "analyze",     "Run the lexer on every item in a JSON steno translations dictionary.")
add("spectra_lexer.console",  "console",     "Run commands interactively from console.")
add("spectra_lexer.console",  "index",       "Analyze a translations file and index each one by the rules it uses.")
add("spectra_lexer.gui_http", "http",        "Run the application as an HTTP web server.")
add("spectra_lexer.gui_qt",   "gui",         "Run the application as a standalone GUI (default).", is_default=True)
add("spectra_lexer.plover",   "plover_test", "Run the GUI application in Plover plugin test mode.")


def main(_script:str="", mode:str="", *argv:str) -> int:
    """ Look up an entry point using the first command-line argument, call it with the rest, and return the exit code.
        If the return value isn't an integer, cast it to bool and return its inverse (so True is success). """
    func = entry_points(mode)
    if func is None:
        return -1
    result = func(*argv)
    if isinstance(result, int):
        return result
    return not result


if __name__ == '__main__':
    sys.exit(main(*sys.argv))

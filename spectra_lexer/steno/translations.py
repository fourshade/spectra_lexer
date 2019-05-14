from configparser import ConfigParser
import json
from typing import Dict, List, Union

from spectra_lexer.core import COREApp, Component, Resource
from spectra_lexer.system import CmdlineOption, ConsoleCommand, SYSControl, SYSFile
from spectra_lexer.types.codec import JSONDict
from spectra_lexer.utils import ensure_iterable

# Plover's app user dir and config filename. Dictionaries are located in the same directory.
_PLOVER_USER_DIR = "~plover/"
_PLOVER_CFG_FILENAME = _PLOVER_USER_DIR + "plover.cfg"
# By default, the sentinel value 'PLOVER' means 'try and find the files from Plover on start'.
_PLOVER_SENTINEL = "PLOVER"


class TranslationsDictionary(JSONDict):
    pass


class LXTranslations:

    @ConsoleCommand("translations_load")
    def load(self, filenames:Union[str, List[str]]="") -> TranslationsDictionary:
        raise NotImplementedError

    @ConsoleCommand("translations_save")
    def save(self, d:Dict[str, str], filename:str="") -> None:
        raise NotImplementedError

    class Dict:
        translations: TranslationsDictionary = Resource()


class TranslationsManager(Component, LXTranslations,
                          COREApp.Start):
    """ Translation parser for the Spectra program. The structures are just string dicts
        that require no extra processing after conversion to/from JSON. """

    files = CmdlineOption("translations-files", default=[_PLOVER_SENTINEL],
                          desc="JSON translation files to load on startup.")
    out = CmdlineOption("translations-out", default="translations.json",
                        desc="Output file name for steno translations.")

    def on_app_start(self) -> None:
        self.load()

    def load(self, filenames:Union[str, List[str]]="", **kwargs) -> TranslationsDictionary:
        """ Load and merge translations from disk. Only send an engine command if at least one file was found. """
        patterns = ensure_iterable(filenames or self.files)
        if _PLOVER_SENTINEL in patterns:
            patterns = self._plover_files()
        d = TranslationsDictionary.decode(*self.engine_call(SYSFile.read_all, patterns))
        if d:
            self.engine_call(self.Dict, d)
        return d

    def save(self, d:TranslationsDictionary, filename:str="", **kwargs) -> None:
        """ Save a translations dict directly into JSON. If no save filename is given, use the default. """
        self.engine_call(SYSFile.write, filename or self.out, d.encode())

    def _plover_files(self) -> List[str]:
        """ Attempt to find the local Plover user directory and, if found, decode all dictionary files
            in the correct priority order (reverse of normal, since earlier keys overwrite later ones). """
        try:
            cfg = ConfigParser()
            data = self.engine_call(SYSFile.read, _PLOVER_CFG_FILENAME)
            cfg.read_string(data.decode('utf-8'))
            section = cfg['System: English Stenotype']['dictionaries']
            # The section we need is read as a string, but it must be decoded as a JSON array.
            return [_PLOVER_USER_DIR + e['path'] for e in reversed(json.loads(section))]
        except OSError:
            # Catch-all for file loading errors. Just assume the required files aren't there and move on.
            pass
        except KeyError:
            self.engine_call(SYSControl.status, "Could not find dictionaries in plover.cfg.")
        except ValueError:
            self.engine_call(SYSControl.status, "Problem decoding JSON in plover.cfg.")
        return []

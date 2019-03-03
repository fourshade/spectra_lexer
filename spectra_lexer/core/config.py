from spectra_lexer import Component, on, pipe
from spectra_lexer.options import CFGOption, CommandOption
from spectra_lexer.utils import str_eval


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. Config file may be specified with command line arguments. """

    ROLE = "config"
    file: str = CommandOption("~/config.cfg", "Config .cfg or .ini file to load at startup and save updates.")

    _cfg_info: dict  # Dict with detailed config info from active components.

    def __init__(self):
        super().__init__()
        self._cfg_info = {}

    @pipe("start", "config_load")
    def start(self, **opts) -> tuple:
        return ()

    @pipe("config_load", "new_config")
    def load(self, filename:str="") -> dict:
        """ Load all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = self.engine_call("file_load", filename or self.file)
        except OSError:
            return {}
        # Try to convert Python literal strings to objects. This fixes crap like bool('False') = True.
        for page in d.values():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    page[opt] = str_eval(val)
        return d

    @on("new_config_info")
    def set_config_info(self, role:str, name:str, option:CFGOption):
        """ Store a single config option by owner role and option key. """
        self._cfg_info.setdefault(role, {})[name] = option

    @pipe("config_dialog", "new_config_dialog")
    def dialog(self) -> dict:
        return self._cfg_info

    @pipe("config_save", "new_config")
    def save(self, d:dict, filename:str="") -> dict:
        """ Update config options, send them to the components, and save them to disk.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default file. """
        self.engine_call("file_save", (filename or self.file), d)
        return d

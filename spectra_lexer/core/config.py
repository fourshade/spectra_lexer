from spectra_lexer import Component
from spectra_lexer.utils import str_eval


class ConfigManager(Component):
    """ Configuration parser for the Spectra program. Config file may be specified with command line arguments. """

    ROLE = "config"
    file = Option("cmdline", "config-file", "~/config.cfg", "Config .cfg or .ini file to load at startup.")

    _cfg_info: dict = {}  # Dict with detailed config info from active components.

    @on("config_options")
    def get_options(self, options:list):
        """ Store all active config option info by owner role and option name. """
        d = self._cfg_info = {}
        for (key, opt) in options:
            sect, name = key.split(":", 1)
            d.setdefault(sect, {})[name] = opt

    @pipe("start", "config_load")
    def start(self, **opts) -> tuple:
        """ Add the config dialog command and load the config file. """
        self.engine_call("new_menu_item", "Tools", "Edit Configuration...", "config_dialog")
        return ()

    @on("config_load")
    def load(self, filename:str="") -> None:
        """ Load all config options from disk. Ignore failures and convert strings using AST. """
        try:
            d = self.engine_call("file_load", filename or self.file)
        except OSError:
            return
        # Try to convert Python literal strings to objects. This fixes crap like bool('False') = True.
        for page in d.values():
            for (opt, val) in page.items():
                if isinstance(val, str):
                    page[opt] = str_eval(val)
        # Update any components using these config settings.
        self._set_options(d)

    @pipe("config_dialog", "new_config_dialog")
    def dialog(self) -> dict:
        return self._cfg_info

    @pipe("config_save", "file_save")
    def save(self, d:dict, filename:str="") -> tuple:
        """ Send updated config options to the components and save them to disk.
            Saving should not fail silently, unlike loading. If no save filename is given, use the default file. """
        self._set_options(d)
        return (filename or self.file), d

    def _set_options(self, d:dict):
        """ Update all active components with new options. May not be thread-safe. """
        for sect, page in d.items():
            for name, val in page.items():
                self.engine_call(f"set_config_{sect}:{name}", val)

from spectra_lexer.plover.config import find_dictionaries
from spectra_lexer.util.cmdline import CmdlineOptions
from spectra_lexer.util.path import module_directory, PrefixPathConverter, user_data_directory

# The name of the root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]
PLOVER_APP_NAME = "plover"


class SpectraOptions(CmdlineOptions):
    """ Contains all command-line options necessary to build essential components. """

    ASSET_PATH_PREFIX = ":/"           # Prefix that indicates built-in assets.
    USER_PATH_PREFIX = "~/"            # Prefix that indicates local user app data.
    PLOVER_SENTINEL = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.

    def __init__(self, app_description="Running Spectra as a library (should never be seen).") -> None:
        super().__init__(app_description)
        self.add("log", self.USER_PATH_PREFIX + "status.log",
                 "Text file to log status and exceptions.")
        self.add("keymap", self.ASSET_PATH_PREFIX + "assets/key_layout.cson",
                 "CSON file with static steno key layout data.")
        self.add("rules", self.ASSET_PATH_PREFIX + "assets/rules.cson",
                 "CSON file with static steno rule data.")
        self.add("board-defs", self.ASSET_PATH_PREFIX + "assets/board_defs.cson",
                 "CSON file with static steno board definition data.")
        self.add("translations", [self.PLOVER_SENTINEL],
                 "JSON translation files to load on start.")
        self.add("index", self.USER_PATH_PREFIX + "index.json",
                 "JSON index file to load on start and/or write to.")
        self.add("config", self.USER_PATH_PREFIX + "config.cfg",
                 "Config CFG/INI file to load at start and/or write to.")
        converter = PrefixPathConverter()
        asset_path = module_directory(ROOT_PACKAGE)
        converter.add(self.ASSET_PATH_PREFIX, asset_path)
        user_path = user_data_directory(ROOT_PACKAGE)
        converter.add(self.USER_PATH_PREFIX, user_path)
        self._convert_path = converter.convert

    def keymap_path(self) -> str:
        return self._convert_path(self.keymap)

    def rules_path(self) -> str:
        return self._convert_path(self.rules)

    def board_defs_path(self) -> str:
        return self._convert_path(self.board_defs)

    def log_path(self) -> str:
        """ Return the path for the log file, creating empty directories to its location if necessary. """
        return self._convert_path(self.log, make_dirs=True)

    def translations_paths(self) -> list:
        """ Return a list of full file paths to the translation dictionaries. """
        filenames = []
        for f in self.translations:
            if f == self.PLOVER_SENTINEL:
                plover_user_path = user_data_directory(PLOVER_APP_NAME)
                filenames += find_dictionaries(plover_user_path, ext=".json", ignore_errors=True)
            else:
                filenames.append(self._convert_path(f))
        return filenames

    def index_path(self) -> str:
        """ Return the full file path to the examples index, adding directories if it doesn't exist. """
        return self._convert_path(self.index, make_dirs=True)

    def config_path(self) -> str:
        """ Return the full file path to the config file, adding directories if it doesn't exist. """
        return self._convert_path(self.config, make_dirs=True)

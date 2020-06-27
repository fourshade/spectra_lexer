""" Package for the core components of Spectra. These are the building blocks of practically everything else:

    resource - The most basic lexer operations requires a set of rules that map steno keys to letters as well
    as a steno layout that tells it which keys are valid and where they are. These must be loaded from disk.
    Graphical displays may also require some outside information to tell what to render and where.
    The first step on startup is to load everything from the built-in assets directory.

    engine - Glues all primary components together, handling communication and passing information between them.
    The engine layer is intended to be called directly by applications i.e. as a library.

        search - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality, including normal
        translation search, stroke search, regex search, and even search from a pre-analyzed index of rule examples.

        analysis - Handles tasks relates to the lexer, such as parsing rules into categories, converting key formats,
        and running queries. There is also a facility for bulk processing of large numbers of translations in parallel.

            lexer - A translation consists of a series of strokes mapped to an English word, and it is the lexer's job
            to match pieces of each using a dictionary of rules it has loaded.

        display - Generates all graphical output. This is the most demanding job in the program. Steno rules may
        be parsed into a tree of nodes, each of which may have information that can be displayed in several forms.
        All information for a single node is combined into a display "page", which may be loaded into the GUI.
        All display pages for to a single rule or lexer query are further stored in a single data object.
        This allows for fewer requests in HTTP mode and more opportunities for caching.

            graph - The lexer output (usually a rule constructed from user input) may be sent to this component
            which puts it in string form for the GUI to display as a text graph breakdown. After display, the mouse
            may be moved over the various rules to highlight them and show a more detailed description.

            board - A steno board layout is also shown below the graph using information from the lexer output.
            Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
            different color. The board layout is updated to show more detail when the mouse is moved over the graph.

    gui - As the frontend, the GUI variants are conceptually separate from the other components. The GUI may run
    on a standalone framework with its own threads, meaning we can't directly call into the engine without locks.
    Most interaction with the rest of the app involves a single object representing the "state" of the GUI.
    It is a simple data object which is passed to the app, updated with changes, then passed back.

    app - Contains the engine and handles user-level tasks such as configuration and GUI requests.

        qt - The primary desktop GUI uses PyQt. There are several useful debug tools available as well.

        plover - There is an entry point hook to allow Plover to load the Qt GUI as a plugin. Search dictionaries will
        come from Plover instead of disk in this mode, and strokes entered by the user will be caught and analyzed.
        Strokes from Plover are handled independently of manual search; the output window will display the last
        translation no matter where it came from.

        http - An HTML version of the GUI using AJAX is accessible by running an HTTP server. There is little
        in the way of performance or security, but it works well enough to run on a Raspberry Pi.

        console - The engine may be run on its own in a Python console. This is usually not terribly useful.

        index - Perform batch index generation directly from a terminal shell.

    __main__ - When spectra_lexer is run directly as a script, the first command-line argument will be used
    to choose one of the application entry points described above, defaulting to the Qt GUI.

    __init__ - Anything using Spectra, including the built-in application objects, must start by calling one of the
    main factory methods on the Spectra class. All entry points to the program descend from this in some manner. """

from spectra_lexer.plover.config import find_dictionaries
from spectra_lexer.resource.io import StenoResourceIO
from spectra_lexer.spc_board import BoardEngine, build_board_engine
from spectra_lexer.spc_graph import build_graph_engine, GraphEngine
from spectra_lexer.spc_lexer import build_analyzer, StenoAnalyzer
from spectra_lexer.spc_search import build_search_engine, SearchEngine
from spectra_lexer.util.cmdline import CmdlineOptions
from spectra_lexer.util.log import open_logger, StreamLogger
from spectra_lexer.util.path import module_directory, PrefixPathConverter, user_data_directory

# The name of the root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]
PLOVER_APP_NAME = "plover"


class Spectra:
    """ Container for all common components, and the basis for using Spectra as a library. """

    def __init__(self, logger:StreamLogger, resource_io:StenoResourceIO, search_engine:SearchEngine,
                 analyzer:StenoAnalyzer, graph_engine:GraphEngine, board_engine:BoardEngine) -> None:
        self.log = logger.log
        self.resource_io = resource_io
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.graph_engine = graph_engine
        self.board_engine = board_engine


class SpectraOptions(CmdlineOptions):
    """ Main factory class. Contains all command-line options necessary to build essential components. """

    ASSET_PATH_PREFIX = ":/"           # Prefix that indicates built-in assets.
    USER_PATH_PREFIX = "~/"            # Prefix that indicates local user app data.
    PLOVER_SENTINEL = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.

    def __init__(self, app_description="Running Spectra as a library (should never be seen).") -> None:
        """ Parse any command-line options, then create the logger. Create empty directories if necessary. """
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

    def log_path(self) -> str:
        """ Return the path for the log file, creating empty directories to its location if necessary. """
        return self._convert_path(self.log, make_dirs=True)

    def keymap_path(self) -> str:
        return self._convert_path(self.keymap)

    def rules_path(self) -> str:
        return self._convert_path(self.rules)

    def board_defs_path(self) -> str:
        return self._convert_path(self.board_defs)

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

    def compile(self, *, parse_args=True) -> Spectra:
        """ From the base directory, load and verify each resource component, then return the complete collection. """
        if parse_args:
            self.parse()
        log_path = self.log_path()
        logger = open_logger(log_path, to_stdout=True)
        r_io = StenoResourceIO()
        keymap = r_io.load_keymap(self.keymap_path())
        keymap.verify()
        rules = r_io.load_rules(self.rules_path())
        valid_rtfcre = keymap.valid_rtfcre()
        delimiters = {keymap.separator_key(), keymap.divider_key()}
        for rule in rules:
            rule.verify(valid_rtfcre, delimiters)
        board_defs = r_io.load_board_defs(self.board_defs_path())
        search_engine = build_search_engine(keymap)
        analyzer = build_analyzer(keymap, rules)
        graph_engine = build_graph_engine(keymap)
        board_engine = build_board_engine(keymap, board_defs)
        return Spectra(logger, r_io, search_engine, analyzer, graph_engine, board_engine)

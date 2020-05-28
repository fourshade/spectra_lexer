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

from spectra_lexer.analysis import StenoAnalyzer
from spectra_lexer.display import BoardEngine, GraphEngine
from spectra_lexer.engine import StenoEngine
from spectra_lexer.plover.config import find_dictionaries
from spectra_lexer.resource.io import ResourceIO
from spectra_lexer.search import SearchEngine
from spectra_lexer.translations import TranslationsIO
from spectra_lexer.util.cmdline import CmdlineOptions
from spectra_lexer.util.log import open_logger
from spectra_lexer.util.path import module_directory, PrefixPathConverter, user_data_directory

# The name of the root package is used as a default path for built-in assets and user files.
ROOT_PACKAGE = __package__.split(".", 1)[0]
PLOVER_APP_NAME = "plover"


class Spectra:
    """ Main factory class. Contains all command-line options necessary to build a functioning engine and app. """

    ASSET_PATH_PREFIX = ":/"           # Prefix that indicates built-in assets.
    USER_PATH_PREFIX = "~/"            # Prefix that indicates local user app data.
    PLOVER_SENTINEL = "$PLOVER_DICTS"  # Sentinel pattern to load the user's Plover dictionaries.
    LAYOUT_CSON = "key_layout.cson"    # Filename for key layout inside resource directory.
    RULES_CSON = "rules.cson"          # Filename for rules inside resource directory.
    BOARD_CSON = "board_defs.cson"     # Filename for board layout inside resource directory.

    def __init__(self, opts:CmdlineOptions=None) -> None:
        """ Parse any command-line options, then create the logger. Create empty directories if necessary. """
        if opts is None:
            opts = CmdlineOptions("Running Spectra as a library (should never be seen).")
        opts.add("log", self.USER_PATH_PREFIX + "status.log",
                 "Text file to log status and exceptions.")
        opts.add("resources", self.ASSET_PATH_PREFIX + "assets/",
                 "Directory with static steno resources.")
        opts.add("translations", [self.PLOVER_SENTINEL],
                 "JSON translation files to load on start.")
        opts.add("index", self.USER_PATH_PREFIX + "index.json",
                 "JSON index file to load on start and/or write to.")
        opts.add("config", self.USER_PATH_PREFIX + "config.cfg",
                 "Config CFG/INI file to load at start and/or write to.")
        opts.parse()
        self._opts = opts
        converter = PrefixPathConverter()
        asset_path = module_directory(ROOT_PACKAGE)
        converter.add(self.ASSET_PATH_PREFIX, asset_path)
        user_path = user_data_directory(ROOT_PACKAGE)
        converter.add(self.USER_PATH_PREFIX, user_path)
        self._convert_path = converter.convert
        self._io = ResourceIO()
        log_path = self._convert_path(opts.log, make_dirs=True)
        logger = open_logger(log_path, to_stdout=True)
        self.log = logger.log

    def translations_paths(self) -> list:
        filenames = []
        for f in self._opts.translations:
            if f == self.PLOVER_SENTINEL:
                plover_user_path = user_data_directory(PLOVER_APP_NAME)
                filenames += find_dictionaries(plover_user_path, ignore_errors=True)
            else:
                filenames.append(self._convert_path(f))
        return filenames

    def index_path(self) -> str:
        path = self._opts.index
        return self._convert_path(path, make_dirs=True)

    def config_path(self) -> str:
        path = self._opts.config
        return self._convert_path(path, make_dirs=True)

    def _resource_path(self, rel_path:str) -> str:
        """ Get a file path relative to the resources directory. """
        return self._convert_path(self._opts.resources, rel_path)

    def build_engine(self) -> StenoEngine:
        """ From the base directory, load and verify each steno resource component, then build the complete engine. """
        keymap = self._io.load_keymap(self._resource_path(self.LAYOUT_CSON))
        keymap.verify()
        rule_parser = self._io.load_rule_parser(self._resource_path(self.RULES_CSON))
        rules = rule_parser.parse()
        valid_rtfcre = keymap.valid_rtfcre()
        delimiters = {keymap.separator_key(), keymap.divider_key()}
        for rule in rules:
            rule.verify(valid_rtfcre, delimiters)
        board_defs = self._io.load_board_defs(self._resource_path(self.BOARD_CSON))
        t_io = TranslationsIO()
        search_engine = SearchEngine()
        analyzer = StenoAnalyzer.from_resources(keymap, rules)
        graph_engine = GraphEngine.from_resources(keymap)
        board_engine = BoardEngine.from_resources(keymap, board_defs)
        return StenoEngine(t_io, search_engine, analyzer, graph_engine, board_engine)

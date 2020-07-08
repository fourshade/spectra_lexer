""" Package for the core components of Spectra. These are the building blocks of practically everything else:

    options - Anything using Spectra, including the built-in application objects, must start by calling the main
    factory method on the Spectra class with configuration options, which reside here.

    resource - The most basic lexer operations requires a set of rules that map steno keys to letters as well
    as a steno layout that tells it which keys are valid and where they are. These must be loaded from disk.
    Graphical displays may also require some outside information to tell what to render and where.
    The first step on startup is to load everything from the built-in assets directory.

    spc - The primary program components. Intended to be used directly by applications i.e. as a library.

        search - Translations for the program to parse have to come from somewhere, and usually it's a JSON
        dictionary loaded from outside. The search component handles all search functionality, including normal
        translation search, stroke search, regex search, and even search from a pre-analyzed index of rule examples.

        lexer - A translation consists of a series of strokes mapped to an English word,
        and it is the lexer's job to match pieces of each using a dictionary of rules it has loaded.
        There is also a facility for bulk processing of large numbers of translations in parallel.

        graph - The lexer output (usually a rule constructed from user input) may be sent to this component
        which puts it in string form for the GUI to display as a text graph breakdown. After display, the mouse
        may be moved over the various rules to highlight them and show a more detailed description.

        board - A steno board layout is also shown below the graph using information from the lexer output.
        Each stroke is shown separately, with certain rules shown as "compound" keys (such as `n` for -PB) in a
        different color. The board layout is updated to show more detail when the mouse is moved over the graph.

    gui - As the frontend, the GUI variants are conceptually separate from the other components. The GUI may run
    on a standalone framework with its own threads, meaning we can't directly call into the engine without locks.

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

        discord - A bot for Discord that parses user queries into board diagrams. Requires a good search dictionary.

    __main__ - When spectra_lexer is run directly as a script, the first command-line argument will be used
    to choose one of the application entry points described above, defaulting to the Qt GUI. """

from spectra_lexer.options import SpectraOptions
from spectra_lexer.resource.io import StenoResourceIO
from spectra_lexer.spc_board import BoardEngine, build_board_engine
from spectra_lexer.spc_graph import build_graph_engine, GraphEngine
from spectra_lexer.spc_lexer import build_analyzer, StenoAnalyzer
from spectra_lexer.spc_search import build_search_engine, SearchEngine
from spectra_lexer.util.log import open_logger, StreamLogger


class Spectra:
    """ Container for all common components, and the basis for using Spectra as a library. """

    def __init__(self, resource_io:StenoResourceIO, search_engine:SearchEngine, analyzer:StenoAnalyzer,
                 graph_engine:GraphEngine, board_engine:BoardEngine, logger:StreamLogger,
                 translations_paths:list, index_path:str, cfg_path:str) -> None:
        self.resource_io = resource_io
        self.search_engine = search_engine
        self.analyzer = analyzer
        self.graph_engine = graph_engine
        self.board_engine = board_engine
        self.logger = logger
        self.translations_paths = translations_paths
        self.index_path = index_path
        self.cfg_path = cfg_path

    @classmethod
    def compile(cls, opts:SpectraOptions=None, *, parse_args=True) -> 'Spectra':
        """ From command-line options, load and verify each resource component, then return the complete collection. """
        if opts is None:
            opts = SpectraOptions()
        if parse_args:
            opts.parse()
        r_io = StenoResourceIO()
        keymap_path = opts.keymap_path()
        keymap = r_io.load_keymap(keymap_path)
        keymap.verify()
        rules_path = opts.rules_path()
        rules = r_io.load_rules(rules_path)
        valid_rtfcre = keymap.valid_rtfcre()
        delimiters = {keymap.separator_key(), keymap.divider_key()}
        for rule in rules:
            rule.verify(valid_rtfcre, delimiters)
        board_defs_path = opts.board_defs_path()
        board_defs = r_io.load_board_defs(board_defs_path)
        search_engine = build_search_engine(keymap)
        analyzer = build_analyzer(keymap, rules)
        graph_engine = build_graph_engine(keymap)
        board_engine = build_board_engine(keymap, board_defs)
        log_path = opts.log_path()
        logger = open_logger(log_path, to_stdout=True)
        translations_paths = opts.translations_paths()
        index_path = opts.index_path()
        cfg_path = opts.config_path()
        return Spectra(r_io, search_engine, analyzer, graph_engine, board_engine,
                       logger, translations_paths, index_path, cfg_path)
